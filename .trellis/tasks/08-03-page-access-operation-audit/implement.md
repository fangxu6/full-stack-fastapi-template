# IAM audit vertical slice implementation plan

## Ordered checklist

1. Reconcile the final PRD and load the backend/frontend database and
   cross-layer specs before code changes. Confirm the current Alembic head and
   generated-client workflow.
2. Add `AuditEvent` enums, model, schemas, and the `audit_` Alembic migration.
   Create PostgreSQL enums before the table, use UTC timestamps and BIGINT
   identity, add explicit indexes/comments, and implement the downgrade guard.
3. Implement the typed writer and allowlists in `backend/app/modules/audit`.
   Provide same-session success writes and independent-session failure/denial
   writes. Add the 365-day batch cleanup service and scheduler task.
4. Add backend capture boundaries:
   - enrich `permission_required()` with route/request context and durable
     backend denial capture;
   - wrap the five IAM mutation operations with the shared operation helper;
   - add the Platform Administrator query dependency, list endpoint, and
     page-access ingestion endpoint;
   - preserve existing error payloads and request IDs.
5. Add the frontend contract and UI:
   - report IAM page guard denials without blocking navigation;
   - report successful users/roles page mounts once per transition;
   - add the Platform Administrator-only `/admin/audit` route and paginated
     query table with filters; provide no export button or endpoint.
6. Regenerate the OpenAPI client and review the generated diff. Keep route
   files thin and keep audit orchestration in module services/hooks.
7. Add focused backend, migration, frontend, and API E2E tests from
   `e2e-api-tests.md`. Include rollback, missing-related-row, unknown-enum,
   redaction, and cleanup-boundary cases.
8. Run the quality gate on a fresh isolated database, inspect migration
   comments/enums, run frontend checks, and perform a staged diff review before
   requesting `task.py start` or implementation approval.

## Validation commands

Run the backend commands from `backend/` and the frontend commands from
`frontend/`:

```powershell
cd backend
$env:POSTGRES_DB = 'aiadmin_audit_test'
uv run alembic upgrade head
uv run pytest -q tests/modules/audit tests/api/routes/test_audit.py
uv run pytest -q tests/modules/iam tests/api/routes/test_iam.py
bash scripts/lint.sh
cd ..
bash ./scripts/generate-client.sh
cd frontend
pnpm lint
pnpm typecheck
```

Use a second fresh `_test`/`_pytest` database for API E2E mutations. Before
completion, run the repository's full backend suite against a clean isolated
database and verify `git diff --check` plus generated-client consistency.

## Risky files and rollback points

- Alembic revision and `backend/app/models/audit.py`: migration failure or
  enum mismatch blocks deployment; downgrade is allowed only for an empty
  audit table.
- `permission_required()` and IAM routers: a capture exception must not turn a
  permission denial into a 500 or leak request data.
- `WriteSessionDep` operation wrapper: same-transaction success and independent
  failure persistence must be covered before broad tests.
- Frontend guards and generated client: audit reporting must remain
  best-effort for navigation, while the query page must fail closed for
  non-administrators.

If implementation must roll back, revert application code and leave the audit
table/events intact. Remove the migration only before it is applied anywhere;
otherwise use the guarded downgrade after an explicit evidence backup decision.

## Review gates before activation

- PRD decisions are all resolved and the convergence pass removes temporary
  brainstorm sections.
- `design.md`, `implement.md`, and `e2e-api-tests.md` are reviewed together.
- No task status change or source implementation occurs until the product
  owner approves these planning artifacts and `task.py start` is explicitly
  requested.
