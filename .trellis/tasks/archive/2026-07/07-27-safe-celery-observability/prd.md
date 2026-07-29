# 安全 Celery 任务观测

## Goal

在所有应用 Celery 任务的生命周期内提供最小、统一且安全的日志关联信息，使任务开始、成功和失败可运维追踪，但不把日志变成业务状态或敏感数据存储。

## Confirmed Facts

- `backend/app/core/celery.py` 注册 core、inventory 和 scheduler 任务；配置已经使用默认单队列和 at-least-once ACK 策略。
- `backend/app/core/observability.py` 目前只支持 HTTP request context 与封闭 `log_event()` 事件集合，contextvars 会被 HTTP middleware 清理。
- `runtime.ping`、每日测试邮件、库存日报和 scheduler 都是已注册任务；任务仍需在 PostgreSQL 持久化自己的业务状态。
- scheduler runtime settings 在 Celery app 创建前通过 `validate_scheduler_runtime_settings()` 显式校验；signal 不承担进程启动校验。
- 本地运行时为 Celery `5.6.3`。应用任务由单一 `celery_app` 注册：`runtime.ping`、`runtime.send_test_email`、`inventory.daily_report.deliver`、`scheduler.scan_due_jobs`、`scheduler.execute_run` 与 `scheduler.cleanup_runs`；后续 outbox 任务应自动获得同一观测契约。
- 当前日志规范和 ADR 已声明 task context 只能含 `task_id`/`task_name`，但实现尚未声明 task 事件或 task 字段，属于待实现的规范与代码差异。
- Celery 官方 signal 语义表明：`task_prerun` 和 `task_postrun` 都可能提供 args、kwargs、result、exception 或 traceback。handler 必须显式忽略这些值；不能以 `**kwargs` 透传或序列化 signal payload。
- `task_postrun` 在每次已执行的任务尝试后触发，作为统一的无条件清理边界；`after_return` 不覆盖 `RETRY`、`REJECTED` 或 `IGNORED`，不能承担每次尝试的清理。Celery task ID 是调用端提供且可被覆盖的外部 opaque correlation value；日志只接受规范 UUID 形态，不能称为 broker 生成值。
- Celery worker 直接导入 `app.core.celery`，不会经过 FastAPI startup；该模块必须初始化 observability，确保 worker 生命周期事件使用 stdout NDJSON sink。

## Requirements

1. 使用内置 Celery lifecycle signals，不增加 custom `Task` base class、每任务包装器、任务路由或命名队列。
2. `task_prerun` 清理遗留 context，只在 task ID 通过 canonical UUID 校验且 task 属于单一 `celery_app` 的应用任务时，绑定外部提供的 `task_id` 与注册 `task_name`，并以 `INFO` 安全记录 `task.started`；不合格的 ID 或 task name 不得绑定或记录。
3. `task_postrun` 只读取 allowlisted `state` 与 `task_prerun` 已绑定的安全 context：`SUCCESS` 映射为 `task.completed`，`FAILURE` 映射为 `task.failed`，两者仅在该 context 含合法 task identity 时以 `INFO` 记录且不带结果或异常内容；`RETRY`、`REJECTED`、`IGNORED` 等非终态只清理 context，不产生终态事件。无论日志是否成功，都必须在 `finally` 清理 task context。
4. 任何日志、contextvars、Sentry 上下文都不得包含任务参数、run/delivery ID、actor UUID、用户、收件人、配置、token、邮件正文、异常文本或 traceback。
5. `log_event()` 的闭合字段契约扩展为任务生命周期事件及 task-only 字段；HTTP 事件语义保持不变。
6. 业务状态、retry、告警和错误分类仍由模块 PostgreSQL 记录；任务日志不得驱动重试或替代持久化。
7. 使用 `task_prerun` 和 `task_postrun` 作为唯一生命周期边界：前者清理旧 context、校验并绑定安全 task 字段后发出开始事件；后者仅按 allowlisted state 映射事件，并在 `finally` 清理。不得读取 signal 提供的 args、kwargs、result、exception、traceback 或 request headers。
8. task name 的接纳边界必须以单一应用实例和规范化的应用任务名定义，不能把动态 `celery_app.tasks` 全表当作安全白名单，也不能让未来业务任务因手写静态名单而失去观测。

## Acceptance Criteria

- [ ] 每个进入 `task_prerun` 的注册应用任务都产生一次 `INFO` 级别的安全开始日志；`SUCCESS`/`FAILURE` 尝试各产生一次对应终态日志，非终态尝试只清理 context，不误报为完成或失败。
- [ ] task context 仅出现合法 `task_id` 与 `task_name`；HTTP context 不污染 task，连续任务之间无 context 泄漏。
- [ ] 日志测试证明参数、邮件地址、JWT、actor UUID、run/delivery ID 和异常文本不会出现在事件中。
- [ ] scheduler runtime startup 校验仍显式执行；signals 不被用于启动校验、事务、SMTP、broker 发布或业务状态改变。
- [ ] 现有 `runtime.ping`、inventory、scheduler 任务测试和结构化 HTTP 日志测试通过。
- [ ] retry、ignore、reject 与 revocation 的日志范围已由产品决策明确；不产生终态事件的执行尝试仍保证 context 清理，且不会把 retry 原因或异常内容写入日志。
- [ ] 全新 worker 子进程只导入 `app.core.celery` 并 eager 执行 `runtime.ping` 时，开始和成功记录均为含 schema fields 的 NDJSON；调用者提供非法 task ID 时，不产生任何 task lifecycle event 且仍完成统一清理。

## Out Of Scope

- 不新增分布式 tracing、APM collector、日志数据库、任务 dashboard 或日志导出凭据。
- 不在 signal 中创建/更新 outbox、scheduler run、inventory report 或审计记录。
- 不记录任务返回值或异常详情，也不修改 Celery 重试/ACK/队列配置。

## Confirmed Review Decisions

- **Lifecycle boundary:** 只使用 `task_prerun` 和 `task_postrun`。`task_postrun` 的 `finally` 是每次执行尝试的统一清理边界；不使用 `task_success`、`task_failure` 或 `after_return` 承担清理。
- **Task ID:** task ID 按外部可控的 opaque correlation value 处理，只接受 canonical、带连字符的小写 UUID；不合格时不绑定、不记录，也不生成替代 ID。
- **Task name:** 以 task 属于单一应用 `celery_app`、名称符合规范 task-name 语法且排除 Celery 内建前缀作为接纳边界。不得把动态 `celery_app.tasks` 全表当作安全白名单，也不得维护会遗漏未来应用任务的静态名称表。
- **Severity:** `task.started`、`task.completed` 和 `task.failed` 统一使用 `INFO`；失败事件不因级别而携带异常文本或 traceback。
- **Non-terminal attempts:** `RETRY`、`REJECTED`、`IGNORED` 和其他未列入 allowlist 的状态不产生终态事件，只执行 context 清理；retry 原因和业务分类继续由业务持久化记录负责。

## Dependencies

- 前置：无运行时依赖；按整体顺序在 P0/P1 后实施，确保后续 outbox worker 从一开始具备统一安全观测。
- 后续：`07-27-generic-email-outbox` 复用本任务的生命周期日志，不自行添加任务包装器。
- 决策依据：`docs/adr/0010-use-safe-celery-task-observability-context.md`。
