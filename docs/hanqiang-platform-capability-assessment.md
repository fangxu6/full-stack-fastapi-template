# hanqiang 平台能力引入评估

> 状态：评估完成，未实施。  
> 依据：`docs/hanqiang-core-contributions/` 的可复用指南，以及当前模板的 CodeGraph 调用关系与源码。  
> 定位：把本仓库发展为可扩展的平台底座，而不是复制另一套业务系统。

## 结论

可以引入，但应分期建设，且不重复实现已有底座。

当前模板已经有 IAM、请求关联、语义审计、带租约/重试的邮件 Outbox、Celery 和可配置 Scheduler。最合适的演进顺序是：

```text
现有基础设施
  -> 事件回调内核 + 最小出站 Webhook
  -> 外部集成能力
  -> 审批流（以真实业务作为第一个消费者）
```

服务通信、WeCom、文件监控等不应默认进入模板：它们只有在第二个独立服务、明确组织通知渠道或具体文件处理需求出现时才有价值。

## 当前能力与文档候选

| 能力 | 当前模板 | 引入结论 | 依据 |
| --- | --- | --- | --- |
| 身份、角色和权限 | 已有 | 复用，不重建 | `backend/app/models/iam.py`、`backend/app/modules/iam/` |
| 语义审计与请求关联 | 已有 | 复用为平台审计出口 | `backend/app/models/audit.py`、`backend/app/modules/audit/` |
| 邮件投递 | 已有 | 复用为首个通知 Adapter，不泛化成消息平台 | `backend/app/models/email.py`、`backend/app/services/email_outbox.py` |
| 异步与计划任务 | 已有 | 复用任务执行、恢复和告警约束，不搬运另一套 Scheduler | `backend/app/modules/scheduler/` |
| 事件回调与 Webhook | 未发现 | 第一候选 | [事件回调平台](hanqiang-core-contributions/event-callback-platform-2026-01.md) |
| 外部集成中心 | 未发现 | 第二候选，依赖事件日志与幂等投递 | [外部集成复用指南](hanqiang-core-contributions/external-integration-reusable-guide.md) |
| 通用审批流 | 未发现 | 第三候选，以库存调整作为首个消费者 | [审批流复用指南](hanqiang-core-contributions/approval-flow-reusable-guide.md) |
| 服务通信管理 | 未发现 | 暂缓，等待多服务事实需求 | [服务通信复用指南](hanqiang-core-contributions/communication-reusable-guide.md) |
| WeCom 通知 | 未发现 | 暂缓，未来只作为通知 Adapter | [WeCom 复用指南](hanqiang-core-contributions/wecom-reusable-guide.md) |
| 通用定时任务平台 | 已有等价能力 | 不引入；只吸收状态与恢复原则 | [定时任务复用指南](hanqiang-core-contributions/scheduled-task-reusable-guide.md) |

库存调整已拆分为 `correction_router.py`、`correction_service.py`、`correction_workflow.py` 和 `correction_attempts.py`，因此适合作为未来审批流的试点；它不是审批内核的字段来源。

## 推荐分期

### 0. 保持并复用现有底座

后续平台任务必须直接使用以下事实源：

- 权限由 IAM 服务端校验；前端仅据此控制可见性。
- 审计继续写入 `AuditEvent`，关联现有请求 ID 和操作者。
- 可恢复的邮件副作用继续写入 `EmailOutbox`；不能把 Celery 入队视为投递成功。
- Celery 任务仅接收 ID 或 JSON 可序列化上下文，在 Worker 中重新读取 PostgreSQL 事实。
- Scheduler 保持 `SchedulerJob`/`SchedulerRun` 的领域所有权；事件和审批不得改写其运行状态。

这些约束已经覆盖了另一项目定时任务文档中最有价值的部分：持久化状态、执行租约、重试恢复和“已入队不等于已完成”。

### 1. 事件回调内核与最小出站 Webhook

这是第一个建议实施的独立任务，但仅在出现至少一个真实领域事件和一个真实消费者时启动。

建议对业务模块暴露一个小接口：发布事件代码、事件快照和关联上下文；模块不直接发 HTTP、不直接访问 Celery，也不自行维护回调状态。平台内部负责：

1. 保存待处理的事件/回调日志并生成 Trace；
2. 提交后投递后台执行；
3. 按固定顺序执行内部动作或经白名单的出站 HTTP；
4. 持久化尝试、错误摘要、重试和死信/人工重放信息。

首版刻意不包括任意 Python 函数路径、完整 JSONPath 方言、级联事件、复杂可视化编辑器或多种消息渠道。先以一个稳定的事件类型和一个经服务端验证的 Webhook Adapter 验证接缝。

**实施门槛**：事件日志有唯一/幂等边界；提交失败不产生投递；投递失败可恢复；重复消息不重复执行非幂等副作用；敏感字段在日志和管理接口中脱敏；外部 URL 受协议、解析地址、端口、重定向和网络出口策略约束。

### 2. 外部集成能力

仅在事件内核已稳定后建设。目标不是“任意 HTTP 配置器”，而是有版本、密钥、审计和固定业务契约的集成模块。

- 入站：固定请求/响应信封、严格 JSON 限制、认证/幂等键、处理租约和审计。
- 出站：受控 HTTP Profile、超时、Header/Body 映射、响应摘要、幂等键和投递尝试记录。
- 条件：后端是唯一判定者；前端编辑器只是辅助，字段目录和运算符由服务端白名单提供。
- 配置更新：并发版本冲突明确返回，密钥和敏感绑定永不回显。

不要在这一步复刻另一项目中与 FT 设备事件、区域字段或特定业务场景相关的映射。

### 3. 审批流

审批内核应等到真实业务有多级、可配置审批需求时再创建。库存调整是首个可验证的候选消费者，但审批内核只接收业务代码、业务快照和适配器命令。

未来任务的最小范围应包括工作流版本、节点实例、待办分配、审批动作、流程审计和超时扫描；串行、AND/OR 并行、退回、重提、催办和可视化编排按真实需求逐项加入。

每个流程、节点和投递状态必须有领域本地的状态迁移矩阵，明确权限、行锁/条件更新、重复命令、超时与陈旧 Worker 结果的行为。审批完成后的通知或外部副作用只通过第一阶段的事件接口发生。

## 不应复制的内容

- 不以另一项目的目录、Mixin 拆分、字段命名或业务对象为模板契约。
- 不创建跨领域的全局状态机、通用 `ALL_TRANSITIONS` 或允许配置任意 Python 调用的执行器。
- 不为了“以后可能用到”提前建设 WeCom、服务通信后台、文件监控或全量集成管理 UI。
- 不把前端权限、Broker 确认或 HTTP 2xx 当成业务状态成功。

## 后续任务与验收门槛

| 后续任务 | 开始条件 | 完成时至少验证 |
| --- | --- | --- |
| 事件回调与 Webhook | 一个真实事件和一个外部/内部消费者 | 幂等、失败恢复、执行审计、SSRF 防护、权限与脱敏 |
| 外部集成 | 已有稳定事件日志；有固定外部契约 | 版本冲突、认证、入站幂等、出站超时/重试、审计 |
| 审批流试点 | 业务需要多级或可配置审批 | 状态矩阵、并发审批、超时、审计、业务适配器隔离 |
| WeCom Adapter | 组织明确采用 WeCom | Token 生命周期、收件人去重、投递日志和人工重试 |
| 服务通信管理 | 出现第二个独立服务 | 端点身份、调用链、失败重试和跨服务审计 |

对于任何 API 面的实施任务，另建 Trellis 子任务并提供数据库迁移、OpenAPI/前端类型更新、最小端到端用例和回滚说明；本报告本身不代表上述能力已经存在。

## 参考

- [hanqiang 通用与核心提交整理](hanqiang-core-contributions.md)
- [事件回调平台](hanqiang-core-contributions/event-callback-platform-2026-01.md)
- [外部集成中心可复用实现指南](hanqiang-core-contributions/external-integration-reusable-guide.md)
- [审批流可复用实现指南](hanqiang-core-contributions/approval-flow-reusable-guide.md)
- [通用定时任务平台复用指南](hanqiang-core-contributions/scheduled-task-reusable-guide.md)
