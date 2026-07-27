# 安全 Celery 任务观测

## Goal

在所有应用 Celery 任务的生命周期内提供最小、统一且安全的日志关联信息，使任务开始、成功和失败可运维追踪，但不把日志变成业务状态或敏感数据存储。

## Confirmed Facts

- `backend/app/core/celery.py` 注册 core、inventory 和 scheduler 任务；配置已经使用默认单队列和 at-least-once ACK 策略。
- `backend/app/core/observability.py` 目前只支持 HTTP request context 与封闭 `log_event()` 事件集合，contextvars 会被 HTTP middleware 清理。
- `runtime.ping`、每日测试邮件、库存日报和 scheduler 都是已注册任务；任务仍需在 PostgreSQL 持久化自己的业务状态。
- scheduler runtime settings 在 Celery app 创建前通过 `validate_scheduler_runtime_settings()` 显式校验；signal 不承担进程启动校验。

## Requirements

1. 使用内置 Celery lifecycle signals，不增加 custom `Task` base class、每任务包装器、任务路由或命名队列。
2. task prerun 清理遗留 context，只绑定 broker 生成的 `task_id` 与注册 `task_name`，并安全记录 `task.started`。
3. task postrun/postfailure 只记录 `task.completed` 或 `task.failed`，可包含安全的结果类别；所有终止路径清理 task context。
4. 任何日志、contextvars、Sentry 上下文都不得包含任务参数、run/delivery ID、actor UUID、用户、收件人、配置、token、邮件正文、异常文本或 traceback。
5. `log_event()` 的闭合字段契约扩展为任务生命周期事件及 task-only 字段；HTTP 事件语义保持不变。
6. 业务状态、retry、告警和错误分类仍由模块 PostgreSQL 记录；任务日志不得驱动重试或替代持久化。

## Acceptance Criteria

- [ ] 所有注册的应用 Celery 任务都产生一次开始和一次终态的安全日志，失败路径也清理 context。
- [ ] task context 仅出现合法 `task_id` 与 `task_name`；HTTP context 不污染 task，连续任务之间无 context 泄漏。
- [ ] 日志测试证明参数、邮件地址、JWT、actor UUID、run/delivery ID 和异常文本不会出现在事件中。
- [ ] scheduler runtime startup 校验仍显式执行；signals 不被用于启动校验、事务、SMTP、broker 发布或业务状态改变。
- [ ] 现有 `runtime.ping`、inventory、scheduler 任务测试和结构化 HTTP 日志测试通过。

## Out Of Scope

- 不新增分布式 tracing、APM collector、日志数据库、任务 dashboard 或日志导出凭据。
- 不在 signal 中创建/更新 outbox、scheduler run、inventory report 或审计记录。
- 不记录任务返回值或异常详情，也不修改 Celery 重试/ACK/队列配置。

## Dependencies

- 前置：无运行时依赖；按整体顺序在 P0/P1 后实施，确保后续 outbox worker 从一开始具备统一安全观测。
- 后续：`07-27-generic-email-outbox` 复用本任务的生命周期日志，不自行添加任务包装器。
- 决策依据：`docs/adr/0010-use-safe-celery-task-observability-context.md`。
