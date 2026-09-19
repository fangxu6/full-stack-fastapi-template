# 技术设计：事件回调内核

> 2026-09-19 复核版；对应 [prd.md](prd.md) R1–R8。实现已按本设计落地；验证证据见 [implement.md](implement.md)。

## 1. 目标、边界与复用

在调用方事务中登记不可变事件，再经现有 Celery 运行时执行代码注册的处理器。PostgreSQL 是发布和投递事实源；Broker 只携带 delivery ID。

- 复用 `app.core.celery:celery_app`、AuditFields、AuditEvent、System Actor 和封闭日志接口。
- 参考 EmailOutbox 的有限重试与 Actor 规则、Scheduler 的**派发租约**与短事务分段；不直接调用其领域状态服务，不抽取跨领域执行框架。
- 当前无统一租户模型。资源 ID/payload 不授予权限；业务适配器未来负责权限、所有权和消费者幂等。
- 本期没有 HTTP、Webhook、密钥、动态配置、业务发布者或前端。生产处理器注册表为空，测试处理器只由测试入口装配。
- 延期能力及启用前置条件见 [deferred-iterations.md](deferred-iterations.md)，审核证据见 [research/requirements-review.md](research/requirements-review.md)。

## 2. 模块与事务所有权

```text
backend/app/models/event.py          # 发布、投递、状态与错误分类
backend/app/modules/events/
    __init__.py
    contracts.py                    # 信封、处理器类型、稳定领域错误
    registry.py                     # 显式代码注册和版本匹配
    service.py                      # 发布及投递状态；无 commit/rollback
    tasks.py                        # 短事务协调、Broker/handler 边界
backend/app/alembic/versions/<rev>_create_event_callback_kernel_tables.py
backend/tests/modules/events/       # 单元、数据库并发、任务与真实运行时测试
```

发布方持有事务。服务只 add/flush；Beat/Worker 的协调入口为每个持久化阶段创建会话并提交，处理器和 Broker 调用期间不保留数据库事务。所有状态迁移只通过事件服务；不在通用 Celery 文件中散布状态逻辑。

## 3. EventEnvelope 与输入约束

| 字段 | 首版契约 |
|---|---|
| `event_id` | 必填 UUID，调用方重试必须复用；唯一发布去重键 |
| `event_type`、`producer` | 必填非空稳定代码，各最多 128 字符；无业务枚举、通配表达式 |
| `schema_version` | 必填正整数；通过注册声明判断支持范围 |
| `resource_type`、`resource_id` | 必填非空字符串，各最多 128 字符；只作定位 |
| `occurred_at` | 必填带时区 datetime，规范化为 UTC；重试不得重新生成事件发生时间 |
| `request_id` | 可空；显式值须匹配现有 32 位小写十六进制规则；缺省读取当前上下文，没有则 null |
| `trace_id` | 可空，提供时为非空字符串且最多 128 字符；缺省为 event_id 的 hex，不创建分布式追踪系统 |
| `idempotency_key` | 可空，提供时为非空字符串且最多 128 字符；缺省为 event_id 字符串，只传递给消费者 |
| `payload` | 必填 JSON object，仅原生 JSON 值、字符串键和有限数值；拒绝 ORM、bytes、datetime、自引用等隐式转换 |

技术安全边界采用规范化 JSON 的 UTF-8 **65,536 字节**上限（含），最大容器嵌套深度 32（顶层 object 为 1）；先做有界遍历再编码，非 ASCII 内容按字节计算。拒绝不能写入 JSONB 的字符串/数值，不把验证异常中的原始输入放入日志。未知顶层字段拒绝。

规范化固定键排序和紧凑分隔符，拒绝 NaN/Infinity；payload 对象键顺序不改变内容，数组顺序、值类型与数值表示按规范化结果比较，不做业务等价推断。普通 frozen 模型不代表嵌套 dict/list 不可变：发布时复制并固定快照，每次 handler 调用从已提交快照构建独立副本，禁止共享 ORM JSON 引用。

### 发布幂等

参与语义比较：`event_type, schema_version, producer, resource_type, resource_id, occurred_at, effective idempotency_key, payload`。不参与比较：`request_id, trace_id`、审计字段和内部主键。首次保存的完整上下文不被重复发布覆盖。

- 相同 event_id/语义内容：返回既有 publication；不重匹配处理器、不创建 delivery、不重复审计。
- 相同 event_id/不同语义内容：抛出稳定 `EventPublicationConflict`，不返回已有 payload。
- 相同 idempotency_key/不同 event_id：是两个事件；消费者自行定义该键的业务唯一性。
- 校验与规范化在事件写入前完成。唯一约束解决竞态；冲突处理采用局部 savepoint 或等价原子写入，不调用外层 session.rollback。仅捕获 event_id 唯一冲突，其它数据库错误不能伪装成重复。
- 新发布、全部投递、发布审计在同一事务完成；任一步失败都不能部分提交。并发重试只在赢家事务完成后读取其事实。调用方捕获局部领域冲突后仍可按自己的事务策略处理其它写入。

## 4. 持久化模型

### EventPublication

BIGINT identity 内部主键；UUID event_id 唯一；保存信封结构字段和 JSONB payload，继承 AuditFields。提交后无业务更新、无运行状态、不提供修改或软删除服务。created_by 保留原始发布者。

### EventDelivery

BIGINT identity 主键；publication_id 外键限制删除；`(publication_id, handler_key)` 唯一。继承 AuditFields，字段至少包括：

| 字段 | 约束 |
|---|---|
| `handler_key` | 非空代码键，最多 128 字符 |
| `state` | `EventDeliveryState`：PENDING、LEASED、RETRY_WAIT、SUCCEEDED、FAILED |
| `attempt_count` | 0..8；每次成功 claim 加 1，包括 claim 后发现处理器不可用 |
| `next_attempt_at` | PENDING/RETRY_WAIT 必填；其余为空 |
| `next_dispatch_at` | PENDING/RETRY_WAIT 必填；同时是当前派发租约的到期时间和条件更新凭据 |
| `lease_token`、`lease_expires_at` | LEASED 时均必填，其余均为空；token 每次 claim 新生成 UUID |
| `last_error_category` | 可空，闭集 EventDeliveryErrorCategory；只保存分类，不保存异常文本 |
| `completed_at`、`failed_at` | 分别仅在 SUCCEEDED、FAILED 时必填且互斥 |

创建时 next_attempt_at/next_dispatch_at 使用登记时间，不使用可能早于现在的 occurred_at。扫描预占时必须保存原 next_dispatch_at；发送失败释放时以 delivery ID、状态和该精确时间做条件更新。这样无需新增派发 token 字段，也能阻止过期的旧扫描器覆盖新预占。用数据库 CHECK 约束状态与字段组合、attempt 范围、payload object；partial indexes 支撑 due 和 expired-lease 查询。所有新表/列/enum/约束具有明确名称和中文表列注释。

仅有一个**状态 enum**；错误分类另用本地 StrEnum 与命名 PostgreSQL enum：HANDLER_NOT_REGISTERED、HANDLER_EVENT_TYPE_MISMATCH、SCHEMA_VERSION_UNSUPPORTED、HANDLER_REJECTED、HANDLER_EXECUTION_FAILED、EXECUTION_LEASE_EXPIRED。Broker 派发失败不是 handler attempt，不覆盖上次执行错误。

## 5. 处理器注册及调用契约

注册项包含稳定 handler_key、明确 event_type/支持的 schema_version 集合和同步 handler。使用固定导入的代码声明；不读取数据库 import 路径，不接受外部 callable 配置，不自动发现插件。启动时装配完成后保持稳定，重复键/非法注册失败。发布端和 Worker 必须加载同一应用版本的声明。

发布只匹配确切 event_type 和受支持版本，并在同一事务中创建 delivery；无匹配只保存 publication，以后注册变更不触发历史补投。Worker 再校验已持久化 handler_key、event_type 与版本，缺失、映射改变或不支持时不调用 handler，记录终态分类。

最小协议为 `handler(envelope) -> None`：正常返回是 SUCCEEDED；专用 `PermanentEventError` 是 HANDLER_REJECTED；其它普通异常是 HANDLER_EXECUTION_FAILED 并走有限重试。错误文本不作为分类，不采用自由文本结果或返回值 payload。进程终止/Worker 丢失由 lease 恢复。

不保证跨事件执行顺序，也不串行化同一资源。多个 handler 独立投递，其中一个失败不撤销另一个的成功。未来消费者须按自己的 handler 身份与 event_id/业务键实现幂等。

## 6. 派发、执行与恢复

### 6.1 Scanner / Broker

每分钟扫描；先恢复最多 100 条到期执行租约，再预占最多 100 条 due delivery，两个查询均稳定排序并使用 FOR UPDATE SKIP LOCKED。due 条件为 state=PENDING/RETRY_WAIT、next_attempt_at<=now 且 next_dispatch_at<=now。

预占只推进 next_dispatch_at=now+派发租约并提交，不改变执行状态和 attempt；该新时间值就是本次派发租约的条件凭据。派发租约首版沿用 CELERY_VISIBILITY_TIMEOUT_SECONDS。逐条 `events.process_delivery(delivery_id)`：

- Celery 参数只有正整数 delivery_id；不用业务 ID 构造 task ID；不发送事件快照。
- 一条发送异常不阻断其它已预占记录。在新事务中，仅当状态和原派发租约的精确 next_dispatch_at 仍匹配，才将该条 next_dispatch_at 改为下一扫描分钟；条件不匹配时不覆盖新预占。
- 预占提交后、发送前崩溃，或 Broker 已收消息但发送者丢失确认：等待派发租约到期再发送；允许重复消息，不能丢记录。
- 不创建新队列、全局 autoretry 或新的派发事实表。

### 6.2 Worker

1. 校验 delivery_id，开启短事务，绑定正确 Actor，行锁后检查 due/state/次数；claim 写新 lease_token、lease_expires_at、attempt+1，清除 next_* 并写审计、提交。
2. 读取已提交事件形成脱离会话的副本，解析注册项，在无数据库事务下调用 handler。
3. 新短事务只在 state=LEASED、token 匹配且 lease_expires_at>now 时接受结果；写状态和 AuditEvent 后提交。过期、重复、旧 token 的成功/失败结果均不写任何状态或语义审计。
4. claim 提交失败不调用 handler；结果提交失败保留原有可恢复事实，不在内存中宣告成功。协调边界抛出仅含固定分类的异常且不携带原始异常链，防止 Celery task_failure 打印 payload/SQL 参数。

执行租约也沿用 CELERY_VISIBILITY_TIMEOUT_SECONDS，但它与派发租约是独立字段/阶段。租约过期**不会停止旧进程或撤销副作用**；本期无 watchdog/心跳/强杀执行器，不承诺避免重叠调用。真实 handler 启用前须定义小于租约的执行超时和副作用幂等；测试用可控进程验证旧 Worker 返回被拒绝。

首个 claim/result 沿用 publication.created_by；重试、lease 恢复、扫描派发用 System Actor。service 不覆盖调用方 Session 中不相关业务操作的 Actor；后台阶段使用独立会话。缺少 Actor 必须 fail closed。

## 状态迁移矩阵（State Transition Matrix）

### event.delivery 状态迁移矩阵

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
|---|---|---|---|---|---|
| (新建) | REGISTER | PENDING | 新 publication 且代码注册匹配 | 两个 next_* 设为登记时间，attempt=0 | 唯一 publication/handler；随业务事务提交 |
| PENDING/RETRY_WAIT | DISPATCH | 不变/拒绝 | 两个 next_* 均到期 | 保存原 next_dispatch_at，推进为派发租约到期时间；提交后发消息 | `SKIP LOCKED`、批量 100；不增加 attempt |
| PENDING/RETRY_WAIT | DISPATCH_FAILURE | 不变/拒绝 | delivery、状态和原 next_dispatch_at 精确匹配 | 改为下一扫描分钟 | 旧发送者不能覆盖新派发或已 claim 记录 |
| PENDING/RETRY_WAIT | CLAIM | LEASED | next_attempt_at 到期，attempt<8 | attempt+1、新 token/lease、清除 next_*、审计 | 行锁；重复消息 no-op；Broker 派发租约不阻止已到达的有效消息 |
| LEASED | HANDLE_SUCCESS | SUCCEEDED | token 匹配且执行租约未过期 | 清理 lease、记录 completed_at、清错误、审计 | 旧结果/重复结果无状态与审计副作用 |
| LEASED | HANDLE_FAILURE | RETRY_WAIT 或 FAILED | 当前有效租约 | 可重试且 attempt<8：next_*=now+15分钟；否则 failed_at；清 lease、审计 | 错误只保存稳定分类 |
| LEASED | HANDLER_NOT_REGISTERED / HANDLER_EVENT_TYPE_MISMATCH / SCHEMA_VERSION_UNSUPPORTED / HANDLER_REJECTED | FAILED | 当前有效租约 | 不执行缺失/不兼容 handler；终态分类与审计 | 修正原稿中“claim 后仍从 PENDING 失败”的矛盾 |
| LEASED | LEASE_EXPIRED | RETRY_WAIT 或 FAILED | lease_expires_at<=now | attempt<8：next_*=now+15分钟；否则终态；清 lease、审计 | 回收不再增加 attempt，行锁/SKIP LOCKED |
| SUCCEEDED/FAILED | 重复消息/旧结果 | 不变/拒绝 | 已终态 | 无 | 终态不复活，无人工重放入口 |

非法状态更新返回稳定领域错误且无局部持久化副作用；查询不到、未到期、终态或 lease 不匹配的后台消息按 no-op 返回。第 8 次成功可成功，第 8 次失败/租约过期进入 FAILED，不发生第 9 次 claim。

## 7. 审计与日志

沿用 AuditEvent，不新增 attempt 审计表。首次发布及 claim/success/retry/failure/lease recovery 分别有固定 action；同事务失败一起回滚。changes 只含 event_id/publication_id/delivery_id、稳定 handler_key、状态、attempt、分类等最小受控摘要，不含 payload、lease token、密钥或异常文本。

纯派发预占是技术协调，不为每次扫描重复生成语义审计；投递生命周期由 delivery 和语义审计共同解释。使用 publication.request_id，不把扫描任务上下文替换为原 HTTP 上下文。既有 AuditEvent 清理仍为严格超过 365 天，不把它描述为永久 attempt 历史。

普通日志只扩展固定事件名（publication.created、delivery.claimed/completed/retry_wait/failed/lease_expired、dispatch.failed，均加 `event.` 前缀），使用现有 facade 的 request_id、elapsed_ms 及已验证 task context。**不添加 event ID、delivery ID、handler key、event type、自由分类等业务字段**，不直接 bind structlog。事件创建/结果成功日志仅在对应事务提交后发出。

handler 异常在调用边界转为稳定分类，不把原异常继续交给 Celery；基础设施边界异常也只暴露固定文本且无原始 cause/context。对日志、Celery 结果后端和异常链注入敏感标记做反向断言。handler 自己的日志也必须遵循现有项目规范，内核不承诺过滤任意业务代码主动输出的内容。

## 8. 迁移、发布、回滚与保留

- 新增 Alembic revision，基于实施时实际 head，建立两表、一个状态 enum、一个错误分类 enum、约束/索引/注释；更新 models/__init__.py 和测试清理顺序（delivery -> publication -> User）。
- 顺序：隔离环境迁移/真实 Worker 验证 -> 部署 additive migration -> 部署一致的应用/Worker/Beat 版本。测试注册入口不得随生产 include 启用。
- 首版无生产发布者，所以无需添加功能开关或动态订阅页面。未来启用业务前先部署兼容 Worker/注册声明，再开放业务发布，避免滚动发布中的 handler 缺失终态。
- 应用回滚先停止事件调用方与事件派发，协调在途处理后回退代码；保留新增表及数据。不得停止其它领域任务作为默认回滚动作。
- drop-table downgrade 只在一次性隔离测试库执行；有数据环境需单独迁移/备份评估，不能按本计划直接删除。
- 首版不清理 publication/delivery，不以 deleted_at 实现软删除。D-001 必须明确真实事件的数据分类、保留周期、容量和清理契约后才可启用；失败记录保留不意味着已经提供人工恢复工具。

## 9. 验证与来源

[implement.md](implement.md) 定义执行顺序和完整质量门槛；[e2e-api-tests.md](e2e-api-tests.md) 覆盖 AC-01–AC-11 的跨层链路。单元/eager 验证输入与状态，独立数据库会话验证锁和事务，真实 Redis/Worker 验证派发与进程故障。没有新 HTTP 路由不等于没有跨层验收。

来源：

- [Hanqiang 事件回调与最小 Webhook prod 契约](../../../docs/hanqiang-core-contributions/prod/prod-event-callback-webhook.md)（范围差异以本任务 PRD 为准）
- [Hanqiang 平台能力评估](../../../docs/hanqiang-platform-capability-assessment.md)
- [异步任务运行时规范](../../spec/backend/async-task-guidelines.md)
- [状态迁移设计规范](../../spec/backend/state-transition-guidelines.md)
- [数据库规范](../../spec/backend/database-guidelines.md)
- [日志规范](../../spec/backend/logging-guidelines.md)
