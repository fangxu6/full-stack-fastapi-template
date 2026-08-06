# Implementation Plan

1. Read the backend scheduler specs and map all current `SchedulerRun` and
   alert field writes.
2. Move run persistence helpers into `run_lifecycle.py` and expose only the
   operations needed by service and task callers.
3. Move alert throttling/outbox persistence into `scheduler_alerts.py`.
4. Replace service/task direct run and alert assignments with delegation while
   preserving transaction ownership and Celery boundaries.
5. Add focused lifecycle and alert tests; update existing scheduler tests only
   where imports or ownership assertions need to follow the new modules.
6. Run focused scheduler tests, API scheduler tests, Celery tests, and the
   backend lint gate.
7. Review `git diff` for unrelated changes and check that no direct
   `SchedulerRun` lifecycle assignments remain outside the lifecycle module.

## Validation

```bash
cd backend
POSTGRES_DB=aiadmin_test uv run pytest tests/modules/scheduler tests/api/routes/test_scheduler.py tests/core/test_celery.py -q
bash scripts/lint.sh
```

Additional source check:

```bash
rg -n "SchedulerRun\.(status|next_dispatch_at|started_at|finished_at|lease_expires_at|attempt_count)|run\.status\s*=|run\.next_dispatch_at\s*=|run\.finished_at\s*=" backend/app/modules/scheduler
```

Expected result: lifecycle assignments are confined to
`run_lifecycle.py`; task/service references are calls to lifecycle helpers.

## Risk Points

- Preserve `FOR UPDATE SKIP LOCKED`, the 100-row dispatch cap, dispatch retry
  minute, and expired execution lease behavior.
- Preserve configuration-invalid versus execution-failed classification.
- Preserve successful-run alert reset and rate-limited failure/overlap/config
  alerts.
- Do not commit a lifecycle helper internally; callers own transaction
  boundaries.

## Validation Results

- `POSTGRES_DB=aiadmin_test uv run pytest tests/modules/scheduler tests/api/routes/test_scheduler.py -q`: 56 passed.
- `POSTGRES_DB=aiadmin_test uv run pytest tests/core/test_celery.py -q`: 16 passed.
- `bash scripts/lint.sh`: passed mypy, ty, Ruff check, and Ruff format checks.
- `python3 ./.trellis/scripts/spec_wiki.py lint`: 0 errors, 0 warnings.
- Source ownership check found no `SchedulerRun` field assignments in
  `service.py` or `tasks.py`; assignments are confined to
  `run_lifecycle.py`.
- API E2E health check was attempted at
  `http://127.0.0.1:8000/api/v1/utils/health-check/` and was blocked because
  no local backend was listening on port 8000. Focused TestClient API coverage
  passed; no development database was used for manual E2E calls.
