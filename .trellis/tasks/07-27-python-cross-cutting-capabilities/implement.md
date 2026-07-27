# Implementation Plan

## Order

父任务不直接实施。依次启动和完成以下子任务：

1. `07-27-request-unit-of-work`
2. `07-27-explicit-audit-actor`
3. `07-27-safe-celery-observability`
4. `07-27-generic-email-outbox`

## Validation

- 每个子任务完成自身 PRD、设计、实现计划、质量检查和提交。
- 父任务在全部子任务完成后运行 `python -m pytest backend/tests/api backend/tests/modules backend/tests/core`，并在隔离 PostgreSQL 执行受影响迁移的 upgrade/downgrade/re-upgrade。
- 如 API 契约或路由变化，执行 `scripts/generate-client.sh` 并按 Workflow Phase 3.4 独立审阅生成文件。

## Review Gates And Rollback Points

- Gate 1：每个子任务的 planning artifacts 审核通过后，才允许启动该子任务。
- Gate 2：子任务质量检查和提交完成后，才可启动下一个子任务。
- Gate 3：全部子任务归档后，父任务执行全量后端质量检查、迁移往返和 API 集成回归。
- 任一 gate 失败，回到对应子任务的 planning artifact；不通过删除旧代码或扩大事务范围来掩盖失败。
- 所有任务在 `task.py start` 前均不修改业务代码；当前父任务和子任务保持 `planning`。
