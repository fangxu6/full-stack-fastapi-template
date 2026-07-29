# Technical Design

## Lifecycle Boundary

在单一 `celery_app` 初始化模块注册 Celery 内置的 `task_prerun` 和 `task_postrun` signals。它们覆盖所有已注册的应用任务，不增加 custom `Task` base class、每任务包装器、任务路由或命名队列。

`task_prerun` 的顺序固定为：

1. 清理遗留的 structlog contextvars，避免 HTTP 或上一项任务的 context 泄漏。
2. 从 signal 提供的 `task_id` 读取外部 correlation value，并校验为 canonical、带连字符的小写 UUID；不生成替代 ID。
3. 从 signal 的 `sender` 取得 task name，仅接纳属于当前单一 `celery_app`、符合规范 task-name 语法且不属于 Celery 内建前缀的应用任务。
4. 仅绑定 `task_id` 和 `task_name`，以 `INFO` 发出 `task.started`。

task ID 是调用端提供且可被调用方覆盖的外部 opaque 标识，不宣称由 broker 生成。task name 边界不能使用动态 `celery_app.tasks` 全表作为白名单，也不能依赖会遗漏未来 outbox 等应用任务的手写静态名称表。ID 或 name 任一校验失败时，不绑定、不记录，但仍允许任务按原 Celery 语义执行。

`task_postrun` 只读取安全的 allowlisted `state` 与 `task_prerun` 已建立的 task context，不读取或转发 `sender`、外部 `task_id`、`args`、`kwargs`、`retval`、`exception`、`traceback`、request headers 或业务记录 ID。只有该既有 context 同时含合法 `task_id` 与 `task_name` 时，才允许发出终态事件；因此被 prerun 拒绝的 identity 不会在 postrun 产生无关联的完成或失败记录：

- `SUCCESS` -> `task.completed`
- `FAILURE` -> `task.failed`
- `RETRY`、`REJECTED`、`IGNORED` 及其他未列入 allowlist 的状态 -> 不产生终态事件

上述三个生命周期事件统一使用 `INFO`。无论状态、绑定结果、日志 sink 是否成功，`task_postrun` 都必须在 `finally` 中清理 task context。非终态尝试的清理不能依赖 `task_success`、`task_failure` 或 `after_return`。

## Observability Facade

`EventName` 和 `log_event()` 显式增加 `task.started`、`task.completed`、`task.failed` 以及 task-only 字段 `task_id`/`task_name`，继续保持闭合签名，禁止开放式 `**kwargs`。由于 Celery signal receiver 的连接约束，handler 可以用 `**signal_payload` 接收 signal 的扩展关键字，但必须立即删除且不得读取、转发或序列化；任务事件由 contextvars 提供 task 字段。

Celery worker 通过 `-A app.core.celery:celery_app` 直接导入该模块，不会运行 FastAPI startup。因此 `app.core.celery` 是 worker 的 observability 初始化入口，必须调用 `configure_observability()`；FastAPI 的既有初始化可重复调用配置函数，但不能作为 worker 的唯一配置路径。

HTTP 调用保持既有 `request_id`/`actor_kind` 等字段语义，task signal 在开始时先清理 context，因此 HTTP context 不会进入 task 事件；postrun 清理后，连续任务之间也不会互相污染。业务状态、retry、告警和错误分类继续由 scheduler/outbox 等模块的 PostgreSQL 记录负责。

## Error Handling And Rollback

- 日志发出失败为 best effort，不能阻塞 task 业务执行或改变 Celery ACK/retry 语义。
- signal handler 只处理观测边界异常，不读取敏感 signal payload；handler 自身异常不得泄漏到任务业务路径。
- 无数据库迁移。回退时移除 signal 注册和 task-only 事件字段，业务任务继续按原有持久化逻辑运行。

## Verification

测试覆盖以下行为：

- canonical UUID 接受，非规范或缺失 task ID 不绑定、不记录；task name 只接受当前应用任务并排除框架任务。
- eager task 的开始/成功/失败事件均为 `INFO`，且事件只含安全 task 字段。
- `SUCCESS`、`FAILURE`、`RETRY`、`REJECTED`、`IGNORED` 状态映射与 postrun `finally` 清理行为。
- 连续任务和 HTTP -> task 场景没有 context 泄漏。
- 参数、邮件地址、JWT、actor UUID、run/delivery ID、返回值和异常文本不会出现在日志事件中；未知关键字在序列化前被拒绝。
- scheduler runtime startup 校验仍在 Celery app 创建前显式执行，signals 不触发 SMTP、broker、数据库事务或业务状态改变。

## Non-Goals

不新增分布式 tracing、APM collector、日志数据库、任务 dashboard 或日志导出凭据；不在 signal 中创建/更新 outbox、scheduler run、inventory report 或审计记录；不记录任务返回值或异常详情，也不修改 Celery 重试、ACK 或队列配置。
