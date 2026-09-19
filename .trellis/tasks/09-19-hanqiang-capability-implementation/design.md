# 技术设计：事件回调内核

## 1. 目标与边界

本期交付一个不绑定业务和外部系统的事件回调内核。它负责把业务事务中的事件快照可靠地登记为事件发布记录，并为未来的代码注册处理器提供持久化、异步、幂等、租约、失败恢复和审计接缝。

本期不实现：

- 具体业务事件发布者、业务字段和领域状态迁移；
- 出站 Webhook、HTTP 客户端、签名、SSRF 策略和 Secret；
- 入站回调、动态订阅、数据库配置的执行器、规则表达式和管理 UI；
- 任意 Python 路径、动态 import、脚本执行或级联编排；
- 前端页面、公开 HTTP API 和生成客户端。

测试假处理器只用于验证内核，不作为运行时默认处理能力。

## 2. 当前模板事实与复用边界

- 新能力属于带有持久化异步工作和事件边界的模块，放入 `backend/app/modules/events/`；SQLModel 表继续放在 `backend/app/models/event.py`，并从 `backend/app/models/__init__.py` 导入。
- 复用 `app.core.celery:celery_app`、JSON-only Celery 参数、系统 Actor 初始化、`EmailOutbox` 的 due scan/lease/claim/complete/fail 形状和 `SchedulerRun` 的过期 lease 约束。
- 复用 `AuditEvent` 与 `modules.audit.service.append_audit_event`，不另建事件审计表；事件 payload 不写入结构化日志和审计 changes。
- 复用 `current_request_id()` 与任务生命周期日志。新增事件日志名和最小事件标识字段时，遵循 `core.observability.log_event()` 的白名单和脱敏边界。
- 当前代码没有 `tenant_id`、组织或工作空间模型。内核不新增伪租户字段，也不声称提供租户隔离；未来业务适配器必须在自己的资源授权边界中处理所有权。
- 数据库仍以 PostgreSQL 为事实源，所有新表和列必须有中文数据库注释；新表使用 BIGINT identity 主键，事件对外去重标识使用 UUID。

## 3. 模块结构

```text
backend/app/
├── models/event.py
├── modules/events/
│   ├── __init__.py
│   ├── contracts.py       # 事件信封、处理器协议和处理结果
│   ├── registry.py        # 代码注册的稳定处理器键；不读取数据库 import 路径
│   ├── service.py         # 发布、登记、状态迁移、lease、恢复
│   └── tasks.py           # due scan 与单条 delivery Celery 任务
└── alembic/versions/<rev>_create_event_callback_kernel_tables.py
```

测试放在 `backend/tests/modules/events/`，模型注释和迁移约束可在同一测试包中验证。

## 4. 契约与数据模型

### 4.1 EventEnvelope

内存中的不可变 Pydantic 契约，未来业务模块通过 `publish()` 提供。最小字段：

| 字段 | 约束 |
|---|---|
| `event_id` | UUID；调用方可重试同一事件时必须复用，数据库唯一 |
| `event_type` | 稳定字符串，长度上限 128；内核不维护业务枚举 |
| `schema_version` | 正整数，首版为调用方提供的版本号 |
| `producer` | 稳定模块标识，长度上限 128 |
| `resource_type` / `resource_id` | 资源定位，不携带业务对象全文 |
| `occurred_at` | 带时区 UTC 时间 |
| `request_id` | 可空；默认从当前请求上下文取得 |
| `trace_id` | 可空字符串；没有上游时由发布调用生成 |
| `idempotency_key` | 可空；缺省使用 `event_id`，不在内核中猜测业务唯一性 |
| `payload` | JSON object；只存最小脱敏快照，不存 ORM 对象或凭据 |

内核校验字段长度、UTC 时间、payload 为 JSON object 和 payload 大小上限；不解释业务字段、表达式或 JSONPath。

### 4.2 EventPublication

不可变事件事实表：

- BIGINT identity `id` 作为内部主键；UUID `event_id` 唯一作为幂等/追踪标识；
- 持久化完整事件信封的结构化字段和 JSONB `payload`；
- 继承 `AuditFields`，由调用方当前事务的 Actor 写入；后台恢复由系统 Actor 写入；
- `event_id` 已存在且信封规范化内容相同则返回已有记录，不创建副本；同一 `event_id` 内容冲突则拒绝；
- 发布服务只 `add/flush`，不 `commit`，由业务调用方和现有请求 Unit of Work 决定事务提交；事务回滚不得留下事件。

### 4.3 EventDelivery

按 `(publication_id, handler_key)` 唯一的一条处理记录。处理器由代码注册，不由数据库输入 import 路径：

- `handler_key`：稳定、白名单化的代码键；
- `status`：`PENDING -> LEASED -> SUCCEEDED`，失败可走 `RETRY_WAIT -> LEASED`，达到上限或处理器缺失走 `FAILED`；
- `attempt_count`、`next_attempt_at`、`lease_expires_at`、`last_error_category`、`completed_at`、`failed_at`；
- 继承 `AuditFields`，所有状态变化由事件服务在明确的事务中完成；
- `PENDING` 和 `RETRY_WAIT` 建立 due partial index，`LEASED` 建立 lease partial index；
- `FAILED` 是本期的死信终态，人工重放和历史 attempt 明细留给后续运维任务，不添加占位 API。

如果事件发布时没有匹配的代码处理器，仍保存 `EventPublication`，但不创建 delivery。以后新增处理器不会自动消费历史事件，历史重放需要未来适配任务显式定义。

## 5. 处理器协议与调用链

`registry.py` 提供稳定键到处理函数的进程内注册表，注册项绑定一个或多个明确的 `event_type`。不提供数据库配置、动态 import 或任意 callable 输入。

```text
业务模块
  -> events.publish(session, envelope)
     -> 校验/规范化 envelope
     -> 以同一事务写 EventPublication
     -> 按代码注册表创建 EventDelivery
     -> 返回 publication；不发送 Celery

Celery Beat: events.scan_due
  -> 恢复过期 lease
  -> 查询 due delivery IDs
  -> 提交 lease/recovery 阶段
  -> 逐个发送 events.process_delivery(delivery_id)

Celery Worker: events.process_delivery(delivery_id)
  -> 新会话锁定并 claim PENDING/RETRY_WAIT
  -> 提交 LEASED 阶段
  -> 重新读取 publication，解析白名单 handler_key
  -> 调用 handler(envelope)，handler 不接收 ORM 对象
  -> 新会话以 lease token 条件更新 SUCCEEDED 或 RETRY_WAIT/FAILED
  -> 写 AuditEvent 和结构化结果日志
```

处理器调用发生在数据库提交之后。Worker 在副作用完成后崩溃时可能被重新投递，因此协议明确是 at-least-once；未来处理器必须自行幂等。旧 lease 的成功/失败结果只能成为 no-op，不得覆盖新的尝试。

## 6. 状态迁移矩阵（State Transition Matrix）

### event.delivery 状态迁移矩阵

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
|---|---|---|---|---|---|
| `PENDING` | `CLAIM` | `LEASED` | 到达 `next_attempt_at`，无有效 lease，attempt 未超限 | 增加 attempt，写 lease token/过期时间，写审计 | 行锁保证单一 claim；重复 claim 返回空 |
| `RETRY_WAIT` | `CLAIM` | `LEASED` | 与 `PENDING` 相同 | 同上 | 旧消息不能绕过 next attempt |
| `LEASED` | `LEASE_EXPIRED` | `RETRY_WAIT` 或 `FAILED` | lease 已过期；按 attempt 次数判断 | 清理 lease，写错误类别和下一次时间或终态时间 | `SKIP LOCKED`；过期恢复可安全重复 |
| `LEASED` | `HANDLE_SUCCESS` | `SUCCEEDED` | 回传 lease token 等于当前值 | 清理 lease，写完成时间和审计 | 旧 Worker 返回 no-op；终态不可复活 |
| `LEASED` | `HANDLE_FAILURE` | `RETRY_WAIT` 或 `FAILED` | 回传 lease token 等于当前值 | 清理 lease，写错误类别和下一次时间或终态时间 | 同上；错误类别不保存敏感异常内容 |
| `PENDING/RETRY_WAIT` | `HANDLER_NOT_REGISTERED` | `FAILED` | claim 后无法按稳定键解析处理器 | 写终态和审计 | 配置错误不无限重试 |
| `SUCCEEDED/FAILED` | 任意重复处理 | 不变/拒绝 | 已是终态 | 无 | 安全 no-op |

EventPublication 没有运行状态；它是提交后的不可变事件事实。投递状态不能替代业务事实，也不能表示未来外部系统已完成业务处理。

## 7. 事务、失败恢复与安全

- 事件记录与业务写入必须由调用方放在同一数据库事务中；Celery 只能接收 delivery ID，不能接收 ORM 对象或任意 payload 作为任务参数。
- Celery 使用现有 late ack/worker lost redelivery；PostgreSQL delivery 状态、lease 和 attempt 是唯一事实源。
- 首版沿用现有可验证常量：最大 8 次尝试、15 分钟 retry wait、lease 使用 `CELERY_VISIBILITY_TIMEOUT_SECONDS`；未来外部 Adapter 需要不同策略时单独设计配置契约。
- `payload` 不进入普通日志、任务异常详情或审计 changes；只记录 event type、event ID、delivery ID、handler key、状态和错误分类。
- 本期没有 HTTP，所以不加入 URL、Secret、签名或 SSRF 逻辑；这些只在 D-002 Webhook 任务中实现。
- 当前模板无显式租户模型。发布协议不能把 payload 中的字段当成授权依据，未来业务处理器必须重新查询并校验资源所有权。

## 8. 观测与审计

新增低基数结构化事件：`event.publication.created`、`event.delivery.claimed`、`event.delivery.completed`、`event.delivery.retry_wait`、`event.delivery.failed`、`event.delivery.lease_expired`。日志包含 Request ID、事件/投递标识、event type、handler key、attempt 和耗时，不包含 payload。

每次重要状态迁移通过 `AuditEvent` 记录 action、resource type/id、request ID 和非敏感状态摘要。由于本期没有查询 API，运维验证以 PostgreSQL 记录和结构化日志为准；指标平台接入不作为本期新依赖。

## 9. 兼容、迁移、发布与回滚

- 新增一次 Alembic migration，创建事件发布表、事件投递表、两个状态 enum、约束、中文注释和 partial indexes。
- `models/__init__.py` 必须导入新模型，使 Alembic metadata 和测试 fixture 发现它们。
- `core/celery.py` 增加 events task module 和 due-scan schedule；没有注册生产处理器时扫描不产生 delivery。
- 发布顺序：迁移 -> 应用/Worker 注册 -> 测试假处理器验证 -> 未来业务任务注册真实处理器。
- 回滚先停止事件 task/调用方，再按任务验证过的 downgrade 删除新表；不得回滚已被未来业务引用的事件契约而不提供兼容窗口。

## 10. 验收范围

- `EventEnvelope` 字段、长度、payload 类型/大小、默认 request/trace/idempotency 行为；
- 同 event ID 的幂等发布和冲突拒绝；业务事务回滚不留事件；
- handler 注册键/事件类型匹配、重复注册拒绝和无 handler 只保存事件；
- delivery 合法状态迁移、非法迁移、重复 claim、过期 lease、旧 Worker 结果和终态 no-op；
- 假处理器成功、可重试异常、达到最大次数和未注册处理器；
- Celery eager 任务只传 delivery ID，事件模块 import 不依赖 SMTP/HTTP；
- 迁移 upgrade/downgrade、表/列中文注释、索引和测试数据库清理；
- 结构化日志脱敏、AuditEvent request ID/Actor 和 payload 不泄漏。

本期不创建 `e2e-api-tests.md`：没有新增 HTTP 路由或前端流程，验收使用数据库集成测试、Celery eager 测试和模块单元测试。

## 11. 来源

- [Hanqiang 事件回调与最小 Webhook prod 契约](../../../docs/hanqiang-core-contributions/prod/prod-event-callback-webhook.md)
- [Hanqiang 平台能力评估](../../../docs/hanqiang-platform-capability-assessment.md)
- [异步任务运行时规范](../../../.trellis/spec/backend/async-task-guidelines.md)
- [状态迁移设计规范](../../../.trellis/spec/backend/state-transition-guidelines.md)
- [数据库规范](../../../.trellis/spec/backend/database-guidelines.md)
