# Harden Celery task observability boundary

## Goal

修复 task identity facade 绕过，并补齐真实 eager 失败后成功的生命周期回归测试。

## Requirements

1. `log_event()` 不得接受调用方直接提供的 `task_id` 或 `task_name`。任务 identity 只能由 `task_prerun` 校验后写入的 structlog contextvars 注入，避免绕过 canonical UUID、应用实例和 task-name 接纳边界。
2. 保持 HTTP 与 dependency 事件的现有 facade 行为不变；不新增开放式字段、通用 event builder 或业务日志。
3. 使用真实 Celery eager 执行覆盖一个失败任务和后续 `runtime.ping` 成功任务，验证 `task.started`、`task.failed`、`task.completed` 的顺序、字段隔离、异常文本排除及 context 清理。
4. 不改变 Celery broker、ACK/retry、任务路由、业务持久化或 scheduler 运行时配置。

## Acceptance Criteria

- [ ] 直接向 `log_event()` 提供 `task_id` 或 `task_name` 在 Python 调用边界被拒绝，且不会产生 JSON 记录。
- [ ] task lifecycle 事件仍通过合法 contextvars 输出 canonical `task_id` 与注册 `task_name`。
- [ ] 一个真实 eager 失败任务随后执行成功任务时，输出恰为 `started`、`failed`、`started`、`completed`；没有异常文本、任务参数或前一任务 context。
- [ ] 现有 observability、Celery、scheduler 和 inventory 回归保持通过，结构化 stdout 契约不变。

## Constraints

- `task_postrun` 继续只读取 allowlisted `state` 与已绑定 context，不读取 signal payload、外部 task ID、返回值或异常。
- `task_id` 是调用端提供的 correlation value；非法值必须不进入日志。
- 此任务是已归档 `07-27-safe-celery-observability` 的 review follow-up，不扩展其产品范围。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
