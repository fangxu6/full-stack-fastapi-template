# Implementation Plan

## Ordered Work

1. Add focused regression tests that characterize the current authenticated
   inventory/scheduler writes, scheduler `requested_by` persistence, and
   non-audited daily-report behavior. Keep direct service/worker test setup as
   explicit transaction owners.
2. Add `User.is_system_actor`, `system_actor_key`, a database check constraint,
   and a partial unique key index. Initialize the default `system` account in
   `app.core.db`, add an idempotent provisioning command for custom keys, keep
   every System Actor inactive with no roles, and record the forward-only
   downgrade constraint in the migration header/tests.
3. Implement the session actor helpers and `before_flush` hook near the model/
   database boundary. Test all eight audited models for insert, update,
   soft-delete/restore, missing actor, invalid actor, and immutable creator
   fields before moving any caller.
4. Add `AuditedWriteSessionDep` as a thin composition over `WriteSessionDep` and
   `CurrentUser`. Migrate only inventory and scheduler write endpoints to it;
   prove authentication and write handling share one Session and one commit.
5. Remove inventory service `_audit()`/manual updater logic and scheduler
   `created_*`/`updated_*` assignments. Preserve `requested_by` as a scheduler
   run business field, not audit data.
6. Update the inventory CLI importer to bind an existing active human or
   pre-provisioned System Actor `actor_user_id`, reject missing and inactive
   human actors, remove manual audit assignments, and retain its explicit
   commit/rollback ownership and dry-run behavior.
7. Extend `ScheduledTaskContext` with `actor_id`. In scheduler tasks, resolve
   manual `requested_by` or the System Actor from the durable run; bind before
   each `SchedulerJob` mutation in scan, execution-finalization, bootstrap, and
   alert paths. Leave daily report/delivery technical sessions unchanged.
8. Add System Actor protection in auth, password recovery/reset, user services,
   and IAM role replacement. Filter public lists, use non-disclosing direct-read
   semantics, and retain the existing generic login/recovery responses.
9. Update database and asynchronous-task specs only for durable contracts
   learned while implementing. Do not alter generated frontend client files
   unless an actual OpenAPI diff appears.
10. Run migration, lint, targeted tests, full backend test suite, and isolated
    local API validation. Review the transaction audit so only the request UoW,
    importer, daily report, and scheduler runtime own commits.

## Risky Files And Checkpoints

- `backend/app/models/base.py`: hook must only act on auditable changes; a broad
  dirty-session loop would update rows on read-only flushes.
- `backend/app/api/dependencies/database.py` and `auth.py`: composition must
  reuse the same cached session and must not add a second transaction owner.
- `backend/app/core/db.py`: create the System Actor before scheduler bootstrap;
  keep the first-superuser/RBAC bootstrap invariant intact.
- `backend/app/modules/scheduler/tasks.py`: preserve dispatch leasing, savepoint
  isolation, terminal-state mapping, and post-commit broker dispatch while
  threading only the actor UUID internally.
- `backend/app/modules/inventory/daily_report.py`: verify it receives no
  unrelated actor or audit-field change.
- `backend/app/alembic/versions/`: migration is forward-only after actor use;
  never write a downgrade that drops referenced attribution data.

## Validation

- From `backend/`: `uv run pytest tests/models tests/api/routes/test_inventory.py tests/api/routes/test_login.py tests/api/routes/test_users.py tests/api/routes/test_scheduler.py tests/modules/inventory tests/modules/scheduler -q`
- From `backend/`: `uv run pytest tests/api tests/crud tests/modules -q`
- From `backend/`: `uv run ruff check tests`
- From `backend/`: `bash scripts/lint.sh`
- Set `POSTGRES_DB=aiadmin_test` for every destructive backend test and local
  E2E run. Apply the new migration, initialize twice, provision two distinct
  custom keys, and verify the default key and each custom key have exactly one
  protected System Actor. Exercise downgrade only on a fresh upgraded database
  before any audited row references a System Actor.
- Run the cases in `e2e-api-tests.md` against a temporary local backend on the
  isolated database. Re-query persistence through a fresh Session after each
  successful or rejected request.

## Review Gates

- Verify all eight `AuditFields` models and every direct assignment found in
  inventory, importer, scheduler service, scheduler tasks, and bootstrap code
  have been covered or deliberately excluded with evidence.
- Verify every System Actor cannot acquire a token, receive reset mail, appear
  in a list/detail response, or receive a role mutation.
- Verify manual scheduler execution preserves its human actor through a worker
  retry, while scheduled scanning and alert-only paths use System Actor.
- Verify no actor UUID, email, role, token, task argument, or detached User is
  added to log context, broker messages, or public schemas.

## Execution Results (2026-07-29)

- Isolated database: every destructive command used `POSTGRES_DB=aiadmin_test`.
- Real migration: upgraded `f2a8c7d1e6b4 -> a8b4c2d6e9f0`; a fresh
  `a8b4c2d6e9f0 -> f2a8c7d1e6b4` downgrade and re-upgrade both succeeded.
  After a System-Actor-attributed `ProcessingUnit` was committed, the same
  downgrade correctly raised `Cannot downgrade System Actor support after it
  has audit references`.
- Initialization/provisioning: repeated `init_db()` and two concurrent
  independent Sessions provisioning the same key passed; custom Actor keys are
  idempotent and distinct.
- Target suite: `79 passed, 2 skipped` for the audit model, importer, and
  scheduler tests. API E2E/route suite: `110 passed`.
- Final quality gate: `uv run ruff check app tests`, `uv run ty check app`, and
  `POSTGRES_DB=aiadmin_test uv run pytest -q` all passed; full pytest result:
  `259 passed, 2 skipped`.
