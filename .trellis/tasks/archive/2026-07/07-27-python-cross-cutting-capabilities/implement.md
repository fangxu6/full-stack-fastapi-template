# Implementation Plan

## Order

父任务不直接实施。依次启动和完成以下子任务：

1. `07-27-request-unit-of-work`
2. `07-27-explicit-audit-actor`
3. `07-27-safe-celery-observability`
4. `07-27-generic-email-outbox`
5. `07-29-harden-celery-observability`

## Validation

- 每个子任务完成自身 PRD、设计、实现计划、质量检查和提交。
- 父任务在全部子任务完成后运行 `python -m pytest backend/tests/api backend/tests/modules backend/tests/core`，并在隔离 PostgreSQL 执行受影响迁移的 upgrade/downgrade/re-upgrade。
- 如 API 契约或路由变化，执行 `scripts/generate-client.sh` 并按 Workflow Phase 3.4 独立审阅生成文件。

## Review Gates And Rollback Points

- Gate 1：每个子任务的 planning artifacts 审核通过后，才允许启动该子任务。
- Gate 2：子任务质量检查和提交完成后，才可启动下一个子任务。
- Gate 3：全部子任务归档后，父任务执行全量后端质量检查、迁移往返和 API 集成回归。
- 任一 gate 失败，回到对应子任务的 planning artifact；不通过删除旧代码或扩大事务范围来掩盖失败。
- 所有任务在 `task.py start` 前均不修改业务代码；启动前父任务和子任务均保持 `planning`。

## Gate 3 Completion Record

- 2026-07-30：五个子任务均已归档后，在 `aiadmin_pytest` 运行完整后端测试，结果为 `277 passed, 2 skipped`。
- 2026-07-30：`bash scripts/lint.sh`（mypy、ty、Ruff、Ruff format）与 `git diff --check` 通过。
- 2026-07-30：在隔离 PostgreSQL 执行 `b5c6d7e8f9a0 -> a8b4c2d6e9f0 -> f2a8c7d1e6b4 -> b5c6d7e8f9a0` 的 upgrade/downgrade/re-upgrade 往返。
- 2026-07-30：在独立 API E2E 数据库完成父任务 `e2e-api-tests.md` 覆盖的集成验证；临时服务已停止。
- 2026-07-30：用户确认父任务进入 `in_progress`，仅进行上述集成验收记录和归档收尾。
