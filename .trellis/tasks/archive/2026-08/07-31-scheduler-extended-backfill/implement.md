# D-003 Implementation Plan

## Preconditions And Review Gates

- [x] Review and approve this task's `prd.md`, `design.md`, and
      `e2e-api-tests.md`.
- [x] D-001's static operation-capability contract and its implementation-class
      matrix are complete.
- [x] Use the actual D-001 names: `task_capabilities(class_path=...)` in the
      service and `can_backfill` in public job responses. Do not add a second
      whitelist or change any current inventory class from `False`.
- [x] Keep `ScheduledTask.allow_backfill` default-deny so future implementation
      classes must explicitly declare `True` after defining replay-safe
      historical semantics.
- [x] Run `python ./.trellis/scripts/task.py start
      07-31-scheduler-extended-backfill` only after the user explicitly approves
      task activation.

## Ordered Changes

1. **Backend history bound**
   - Replace the 90-day backfill constant/check with an explicit 365-day
    boundary, inclusive at exactly 365 days and exclusive for future/current or
    older values.
   - Preserve the existing validation order of timestamp, persisted job, Cron,
     then D-001 capability. Every failure must remain before `create_run()`.
   - Keep `SchedulerRunBackfill`, the route path, permission dependency, and
    `create_run()` invocation shape unchanged.
2. **Capability and dispatch audit**
   - Retain the existing `task_capabilities()` call; D-003 adds no new gate and
     does not modify `allow_backfill` on production task classes.
   - Confirm one service call creates no more than one run and does not call a
     Celery task directly.
   - Confirm the existing `create_run()` lock/savepoint and dispatch scanner
     lease/batch cap remain the only concurrency controls; add regression tests
     if a refactor would otherwise weaken them.
3. **Frontend modal**
   - Update `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx` to the
     Shanghai-local 365-day `min`, current `max`, risk/constraint copy, and the
     D-001 capability-dependent action state.
   - Replace the stale 90-day error text while retaining server-error handling.
   - Keep one timestamp, one submit, and no batch UI.
4. **Tests and generated artifacts**
   - Extend service tests with a test-only replay-safe task class for the 365-day
     success and boundary cases; retain the current inventory denial regression.
   - Extend `backend/tests/api/routes/test_scheduler.py` with the cases in
     `e2e-api-tests.md`, including permission and no-side-effect assertions.
   - Add/update focused frontend Playwright coverage for modal bounds, risk copy,
     hidden/disabled disallowed actions, and one-submit behavior if the existing
     scheduler test harness supports it.
   - Do not regenerate `frontend/src/client`: D-003 changes neither endpoint nor
     public schema.

## Validation Commands

Run from the repository root, using the project's isolated test database
convention and never the development database:

```powershell
$env:POSTGRES_DB = "aiadmin_test"
& "D:\scoop\shims\uv.exe" run --directory backend pytest tests/modules/scheduler/test_scheduler_service.py tests/api/routes/test_scheduler.py
& "D:\scoop\shims\uv.exe" run --directory backend ruff check app tests
& "D:\scoop\shims\uv.exe" run --directory backend mypy app
& "D:\scoop\shims\uv.exe" run --directory backend ty check app
Push-Location frontend
& "D:\scoop\shims\bun.exe" x biome ci --no-errors-on-unmatched --files-ignore-unknown=true src tests/scheduler.spec.ts
& "D:\scoop\shims\bun.exe" run build
& "D:\scoop\shims\bun.exe" x playwright test tests/scheduler.spec.ts
Pop-Location
```

For API E2E execution, start/verify the isolated backend and health endpoint
(`http://127.0.0.1:8000/api/v1/utils/health-check/`) and record the concrete
output or blocker in the task journal. Do not use a live development database.

## Risk And Rollback Points

- **Capability drift**: stop before coding if `task_capabilities()` or
  `can_backfill` differs from the documented D-001 contract; do not invent a
  fallback registry or enable a current inventory task.
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

- [x] Focused backend, API E2E, frontend, lint, type, and build checks are green.
- [x] Full applicable backend gate is green on the isolated database.
- [x] `prd.md`, `design.md`, `implement.md`, and `e2e-api-tests.md` match the
      final implementation and D-001 contract.
- [x] Run `trellis-check` before commit; do not commit without separate user
      confirmation.

## Validation Evidence

- Isolated backend: `POSTGRES_DB=aiadmin_test` full pytest completed with 291
  passed and 3 skipped. The scheduler service/API focus completed with 30
  passed after the final capability-matrix assertions.
- Backend quality: Ruff, mypy, and ty all passed. `git diff --check`, Trellis
  task validation, and wiki/spec lint all passed.
- Frontend quality: Biome and the production build passed. Playwright against
  `http://127.0.0.1:8000` completed 4 scheduler checks, including the
  Shanghai-local, minute-safe 365-day modal bound.
- The full pytest fixture clears `aiadmin_test` at teardown; the isolated
  backend was reinitialized with `app/initial_data.py` before browser tests.
  This did not use the development database.
- Generated client artifacts were intentionally untouched: D-003 changes no
  public OpenAPI request or response schema.
