# IAM semantic change audit implementation plan

## Ordered checklist

1. Reconcile the PRD, design, deferred register, and backend database/error
   specs. Confirm the current Alembic head and direct Celery Beat task pattern.
2. Add `AuditEvent`, its migration, table/column comments, JSONB-object check,
   three indexes, and guarded downgrade. Do not create enum types, foreign keys,
   per-entity history tables, or a reader API.
3. Add the small audit-module writer and IAM-owned action/summary allowlists.
   The writer receives server-resolved actor and request IDs only.
4. Update the IAM mutation routes to pass current actor/request context. The
   IAM service captures allowlisted before state and appends exactly one event
   in the existing `WriteSessionDep`. Keep existing exception propagation
   unchanged.
5. Add `cleanup_expired_events()` and the direct daily `audit.cleanup_events`
   Celery Beat task. Do not add a `SchedulerJob`, task schema, bootstrap row, or
   scheduler UI entry.
6. Add focused model/writer/IAM-route/migration tests and the API cases in
   `e2e-api-tests.md`. Prove failed IAM requests create no semantic event.
7. Run backend quality checks on a clean isolated database, verify the catalog
   comments/indexes/check constraint, and inspect the final diff. No frontend
   client generation is needed because this task exposes no new API.

## Validation commands

Run from `backend/` with an isolated database:

```powershell
$env:POSTGRES_DB = 'aiadmin_audit_test'
uv run alembic upgrade head
uv run pytest -q tests/modules/audit tests/modules/iam tests/api/routes/test_iam.py
bash scripts/lint.sh
```

Run the full backend suite against a clean `_test` or `_pytest` database before
activation. Verify the migration catalog with PostgreSQL comments, the three
indexes, the JSONB-object check constraint, and the guarded downgrade. Finish
with `git diff --check`.

## Risky files and rollback points

- The migration and `backend/app/models/audit.py` own an append-only evidence
  table. A downgrade must refuse while rows remain.
- IAM routes must add an event only after their service call succeeds; a domain
  exception must retain its current response and write no event.
- The writer must accept only server-resolved `actor_user_id` and `request_id`
  plus allowlisted summaries. It must never serialize an input model or raw row.
- The direct Beat task must delete only events older than the 365-day cutoff.

Application rollback leaves the table and rows intact. Remove the migration
only before it has been applied anywhere; otherwise use its guarded downgrade
after a reviewed evidence backup decision.

## Review gates before activation

- PRD, design, deferred register, implementation plan, and E2E cases agree on
  successful IAM changes as the only current event source.
- No page, denial, failure, query UI/API, export, trigger, or external sink is
  accidentally exposed by the implementation.
- No task status change or source implementation occurs until the product owner
  approves these planning artifacts and explicitly requests `task.py start`.

## Execution evidence (2026-08-03)

- `bash ./scripts/lint.sh` passed: mypy, ty, Ruff, and backend format checks
  are clean.
- The isolated `aiadmin_test` migration upgraded to head; comments, indexes,
  and the JSONB-object check were inspected. A nonempty downgrade refused, then
  an empty-table downgrade and re-upgrade completed successfully.
- Focused semantic-audit/IAM/API tests passed. They cover all seven IAM action
  codes, response `X-Request-ID` propagation, no event on domain failure,
  mixed state/non-state PATCH minimization, 365-day retention boundary, Celery
  registration, and test isolation.
- Full isolated backend suite result: `308 passed, 3 skipped, 5 failed`. The
  blockers are outside this task: a stale fixed write-route count (`38` versus
  current `40`), two Celery CLI and one FastAPI subprocess tests whose copied
  production environment lacks a valid `REDIS_PASSWORD`, and an inventory
  importer test that sees multiple preexisting `焦糖` ledger rows. None changes
  the audit schema, writer, IAM mutation flow, or retention task.
