# D-003 Implementation Plan

## Preconditions And Review Gates

- [ ] Review and approve this task's `prd.md`, `design.md`, and
      `e2e-api-tests.md`.
- [ ] Complete D-001's static operation-capability contract and its existing
      implementation-class matrix before activating this task.
- [ ] Reconcile the final D-001 helper/field names into this plan; do not start
      with guessed names or add a second whitelist.
- [ ] Run `python ./.trellis/scripts/task.py start
      07-31-scheduler-extended-backfill` only after the user explicitly approves
      task activation.

## Ordered Changes

1. **Backend capability gate**
   - Reuse the D-001 resolver against the persisted job class path in
     `backend/app/modules/scheduler/service.py`.
   - Place the gate before the current timezone, past-time, age, and Cron checks.
   - Return the agreed scheduler validation error and preserve zero-write
     behavior on denial.
2. **Backend history bound**
   - Replace the 90-day backfill constant/check with an explicit 365-day
     boundary, inclusive at exactly 365 days and exclusive for future/current or
     older values.
   - Keep `SchedulerRunBackfill`, the route path, permission dependency, and
     `create_run()` invocation shape unchanged.
3. **Capacity and dispatch audit**
   - Confirm one service call creates no more than one run and does not call a
     Celery task directly.
   - Confirm the existing `create_run()` lock/savepoint and dispatch scanner
     lease/batch cap remain the only concurrency controls; add regression tests
     if a refactor would otherwise weaken them.
4. **Frontend modal**
   - Update `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx` to the
     Shanghai-local 365-day `min`, current `max`, risk/constraint copy, and the
     D-001 capability-dependent action state.
   - Replace the stale 90-day error text while retaining server-error handling.
   - Keep one timestamp, one submit, and no batch UI.
5. **Tests and generated artifacts**
   - Extend service tests for the capability matrix and 365-day boundaries.
   - Extend `backend/tests/api/routes/test_scheduler.py` with the cases in
     `e2e-api-tests.md`, including permission and no-side-effect assertions.
   - Add/update focused frontend Playwright coverage for modal bounds, risk copy,
     hidden/disabled disallowed actions, and one-submit behavior if the existing
     scheduler test harness supports it.
   - Regenerate `frontend/src/client` only when the D-001 public schema changes.

## Validation Commands

Run from the repository root, using the project's isolated test database
convention and never the development database:

```powershell
cd backend
$env:POSTGRES_DB = "aiadmin_d003_test"
uv run pytest tests/modules/scheduler/test_scheduler_service.py tests/api/routes/test_scheduler.py
uv run ruff check app tests
uv run mypy app
uv run ty check app
cd ..\frontend
bun run build
bun run lint
bun run test -- scheduler
```

For API E2E execution, start/verify the isolated backend and health endpoint
(`http://127.0.0.1:8000/api/v1/utils/health-check/`) and record the concrete
output or blocker in the task journal. Do not use a live development database.

## Risk And Rollback Points

- **D-001 contract drift**: stop before coding if the resolver or public field is
  not settled; update the artifacts and obtain review again.
- **Timezone arithmetic**: a local/UTC conversion regression can admit or reject
  the wrong boundary. Keep explicit `+08:00` fixtures and assert persisted UTC.
- **Capability bypass**: test direct service calls as well as HTTP calls; the
  route check alone is insufficient.
- **Active-run regression**: assert a conflict leaves the existing run and other
  jobs unchanged.
- **Dispatch storm**: monkeypatch/inspect dispatch calls and assert one request
  produces one queued row, with no direct broker invocation.
- **Rollback**: revert the 365-day constant and UI bounds only. Preserve already
  created runs and do not add a migration rollback step.

## Completion Gate

- [ ] Focused backend, API E2E, frontend, lint, type, and build checks are green.
- [ ] Full applicable backend gate is green on the isolated database.
- [ ] `prd.md`, `design.md`, `implement.md`, and `e2e-api-tests.md` match the
      final implementation and D-001 contract.
- [ ] Run `trellis-check` before commit; do not commit without separate user
      confirmation.
