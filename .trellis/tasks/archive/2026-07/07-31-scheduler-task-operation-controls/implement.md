# 定时任务人工操作能力实施计划

## Implementation

1. Extend `backend/app/modules/scheduler/contracts.py` with the two permissive `ClassVar[bool]` values on
   `ScheduledTask`; retain its existing config and execution interfaces.
2. Set `allow_backfill = False` on both deployed inventory daily-report task classes in
   `backend/app/modules/inventory/scheduled_tasks.py`; do not change their run implementations.
3. In `backend/app/modules/scheduler/service.py`, add one private or public typed capability helper based on
   `resolve_task_class()`. Use it in `run_now()` and `backfill()` after the job load and before `create_run()`;
   raise `SchedulerValidationError` for a disabled manual operation.
4. Extend `backend/app/schemas/scheduler.py` with required read-only `can_run_now` and `can_backfill` response
   fields. Update `backend/app/modules/scheduler/router.py`'s existing `_job()` conversion to populate both from
   the same service helper for every job response.
5. Run `bash ./scripts/generate-client.sh`. Review only generated client changes that represent the two response
   booleans; do not hand-edit `frontend/src/client/**`.
6. In `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx`, conditionally render the existing immediate
   run and backfill icon buttons from those generated fields. Keep the existing permission guard, mutation paths,
   modal, Shanghai input conversion, and history actions unchanged.
7. Add focused backend service/API tests and update the scheduler browser test to cover capability visibility and
   the no-side-effect rejection path. Do not introduce a migration, seed-data change, or Celery dispatch code.

## Validation

1. `cd backend && uv run pytest tests/modules/scheduler/test_scheduler_service.py tests/modules/scheduler/test_scheduler_tasks.py tests/api/routes/test_scheduler.py`
2. `bash backend/scripts/lint.sh`
3. `bash ./scripts/generate-client.sh`
4. `cd frontend && bun run build`
5. Run the scheduler Playwright test against the isolated API/frontend environment described in
   `e2e-api-tests.md`.

## Review Gates

- Verify that unsupported operations fail before `create_run()` and before the shared dispatcher can see a run.
- Verify that default-true synthetic task classes still create both manual trigger types.
- Verify that API responses never source capability from config JSON and that generated types compile without a
  local replacement type.
- Verify that no change affects automatic run creation, dispatch leases, 90-day backfill validation, or audit
  attribution.

## Rollback

Revert the code and regenerated-client changes together. There is no schema downgrade and no persisted capability
state to repair; pre-existing runs remain untouched.

## Validation Evidence

- `POSTGRES_DB=aiadmin_test uv run pytest tests/modules/scheduler/test_scheduler_service.py tests/modules/scheduler/test_scheduler_tasks.py tests/api/routes/test_scheduler.py`: 27 passed.
- The Bash client-generation wrapper could not locate Windows `uv`; its equivalent native steps exported OpenAPI
  with `uv run`, called the configured frontend generator, normalized generated whitespace, and passed Biome.
- `uv run mypy app`, `uv run ty check app`, `uv run ruff check app`, and `uv run ruff format app --check`: passed.
- `bun run build`: passed.
- With a temporary `aiadmin_test` backend and initialized test account, `bunx playwright test tests/scheduler.spec.ts`:
  2 passed.
