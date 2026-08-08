# Implementation Plan: 主从数据库读写依赖预留

## 1. Prepare Context

- Read the backend database and quality specs before editing.
- Confirm the task remains `planning`; do not run `task.py start` during task creation.
- Preserve unrelated worktree changes and do not create a branch.

## 2. Configuration and Engines

- Add optional `POSTGRES_READ_REPLICA_SERVER` to `backend/app/core/config.py`.
- Add the read-replica URI property using the existing PostgreSQL connection fields.
- Split the current engine declaration into `write_engine` and conditional `read_engine`.
- Keep `engine = write_engine` for existing imports.
- Add the optional setting to `.env.production.example`.
- Do not add a replica service to `compose.yml`.

## 3. Dependencies and Exports

- Add `get_read_db()` and function-scope `ReadSessionDep` to the database dependency module.
- Keep `get_db()` and `get_write_db()` unchanged in transaction behavior.
- Export `ReadSessionDep` through `app.api.dependencies` and `app.api.deps`.
- Keep `SessionDep` in the authentication module and keep it bound to `get_db()`.

## 4. Route Migration

- Change only the scheduler read allowlist in `backend/app/modules/scheduler/router.py`.
- Change only the inventory read allowlist in `backend/app/modules/inventory/router.py`.
- Keep permission and authentication sub-dependencies on the primary SessionDep.
- Do not change users, items, IAM, correction, write routes, services, CRUD functions, or background tasks.

## 5. Documentation

- Update `.trellis/spec/backend/database-guidelines.md` with the three dependency contracts.
- Document that ReadSessionDep is eventually consistent when a replica is configured.
- Document that no automatic primary fallback exists and that clearing the replica setting restores primary reads.

## 6. Tests

- Extend configuration tests for unset and configured replica host behavior.
- Add dependency lifecycle coverage proving ReadSessionDep yields and closes without commit/rollback.
- Preserve and run existing shared-session and WriteSessionDep commit/rollback tests.
- Add route dependency coverage for the read allowlist and verify all HTTP writes still depend on WriteSessionDep.
- Add a no-replica API regression case proving read behavior remains unchanged.

## 7. Verification

Run from the repository root:

```bash
cd backend
uv run pytest tests/api/test_request_unit_of_work.py tests/core/test_config.py
bash scripts/lint.sh
```

Run the task checks without changing task status:

```bash
python3 ./.trellis/scripts/task.py validate reserve-db-read-session-dep
python3 ./.trellis/scripts/task.py list --status planning
```

Do not run PostgreSQL replication setup, `task.py start`, migrations, code generation,
or application implementation as part of this task-creation turn.

## 8. Completion Gate

- `task.json.status` remains `planning`.
- `branch` and `commit` remain unset.
- No application source file is modified by task generation.
- Four planning artifacts are present and validated.
