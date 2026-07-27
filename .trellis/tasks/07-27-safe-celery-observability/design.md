# Technical Design

## Lifecycle Contract

在 Celery app 初始化模块注册框架信号。`task_prerun` 先清理 structlog contextvars，再从 Celery signal 提供的 task/request 读取并校验 `task_id` 和已注册的 `task_name`，绑定这两个字段，发出 `task.started`。`task_success`/`task_failure` 或等价终态 signal 只发出 `task.completed`/`task.failed`，随后无条件清理 context。

应用不读取或序列化 task args、kwargs、return value、exception、traceback、request headers 或业务记录 ID。对于无安全结果类别的失败，事件只标识失败；具体分类继续由 scheduler/outbox 等业务表保存。

## Observability Facade

`EventName` 与 `log_event()` 显式增加三类任务事件及任务字段，维持闭合签名。HTTP 调用保持原字段集合；任务调用不能传 request-specific 字段。测试覆盖未声明关键字在序列化前被拒绝或不可调用。

## Failure And Rollback

- 日志发出失败为 best effort，不能阻塞 task 业务执行或改变 Celery ACK/retry 语义。
- signal handler 自身捕获并吞掉观测异常，但仍在 finally 清理 context。
- 无数据库迁移。回退为移除 signal 注册和 task-only 事件字段，业务任务仍按原持久化逻辑运行。

## Non-Goals

启动配置校验继续在 Celery app 创建前显式执行。signals 不调用 SMTP、broker、数据库事务或服务函数，也不替代 request Unit of Work 或审计 actor。
