# 定时任务 Cron 后续时点预览实施计划

## Delivery Order

1. **Cron preview service contract**
   - Add the fixed count constant and a side-effect-free service helper in
     `backend/app/modules/scheduler/service.py`.
   - Capture the server base time once; iterate the existing `next_run_at()`
     helper exactly five times; convert parser failures to
     `SchedulerValidationError`.
   - Do not add a model, migration, job lookup, task-class lookup, audit actor,
     dispatch call, or Celery task.

2. **Schema and route**
   - Add `SchedulerCronPreviewPublic` in `backend/app/schemas/scheduler.py`.
   - Add `GET /scheduler/cron-preview` in
     `backend/app/modules/scheduler/router.py`, guarded by
     `scheduler.jobs.read`, with only `cron_expression` as input.
   - Regenerate the frontend client using `bash ./scripts/generate-client.sh`;
     never hand-edit `frontend/src/client/**`.

3. **Backend verification**
   - Extend `backend/tests/modules/scheduler/test_cron.py` or the service test
     module with fixed-clock cases for five ordered timestamps, the Shanghai
     boundary, cross-month progression, and a day/week AND expression.
   - Extend `backend/tests/api/routes/test_scheduler.py` with authorized,
     forbidden, and invalid-Cron API cases. Snapshot job/run IDs before each
     response and assert they remain unchanged; mock/observe dispatch so no
     Celery work is published.

4. **Scheduler editor preview**
   - Keep the debounce hook and React Query in
     `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx`; do not
     import inventory feature code or create a shared abstraction.
   - Query after 300ms of stable nonblank Cron input, render loading/current
     result/current inline error states, and ensure a changed input clears old
     result/error while the new query is pending.
   - Format all scheduler page timestamps with explicit `Asia/Shanghai` time
     zone formatting. Keep save, enable/disable, backfill, and history flows
     unchanged.

5. **Browser and generated-contract validation**
   - Add a scheduler Playwright flow that opens the editor, types an unsaved
     Cron, waits for the automatic request, and asserts the five formatted
     Shanghai results and declared base time.
   - Add the invalid-Cron response flow and assert an inline error appears
     without a global notification; change the input and assert the obsolete
     error/result disappears.
   - Verify the generated SDK exposes the preview method and response fields
     through compilation/build rather than direct generated-file tests.

6. **Documentation and review**
   - Keep task artifacts, API E2E plan, and
     `.trellis/spec/backend/async-task-guidelines.md` synchronized with the
     implemented contract.
   - Run the complete quality gate, review the generated-client diff, then
     request implementation approval before `task.py start`.

## Validation Commands

Run the following after implementation in an explicitly isolated environment:

```powershell
& 'D:\scoop\shims\uv.exe' run --directory backend pytest tests/modules/scheduler/test_cron.py tests/modules/scheduler/test_scheduler_service.py tests/api/routes/test_scheduler.py
& 'D:\scoop\shims\uv.exe' run --directory backend mypy app
& 'D:\scoop\shims\uv.exe' run --directory backend ty check app
& 'D:\scoop\shims\uv.exe' run --directory backend ruff check app tests/modules/scheduler/test_cron.py tests/api/routes/test_scheduler.py
bash ./scripts/generate-client.sh
Push-Location frontend
bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true src tests/scheduler.spec.ts
bunx playwright test tests/scheduler.spec.ts
bun run build
Pop-Location
git diff --check
```

Before API E2E cases, verify `GET http://127.0.0.1:8000/api/v1/utils/health-check/`.
For browser flows, verify `http://localhost:5173` separately. Record the chosen
isolated database and any concrete startup blocker in the task validation log.

## Review Gates And Rollback Points

- Confirm a GET request with only `cron_expression` does not acquire a scheduler
  model or call a mutating service before reviewing implementation.
- Confirm the output list is exactly five UTC timestamps, strictly after a
  single server-derived base time, before generating the client.
- Confirm the generated client, page query key, and router input name agree
  before browser testing.
- If rollout must be reverted, remove the read-only endpoint and UI/client
  surface as one change. No database rollback or scheduler-run cleanup exists.

## Implementation Record

- Implemented the read-only route, side-effect-free service helper, public
  schema, regenerated client, page-local 300ms preview, and inline errors.
- Validation used the isolated `aiadmin_test` database. Local Windows excluded
  the repository-default port 8000, so the temporary backend ran on 9000 and
  Vite on 5173 with that backend as its API target; no product configuration
  changed.
- Passed: focused scheduler backend suite (28 tests), backend Ruff check,
  focused backend format check, `mypy app`, `ty check app`, frontend Biome,
  frontend production build, and scheduler Playwright suite (4 tests).
- The full backend format sweep reports three pre-existing unrelated test files
  (`test_ai_removal_migration.py`, `test_audit_actor.py`, and
  `test_importer.py`); they were intentionally left untouched.
