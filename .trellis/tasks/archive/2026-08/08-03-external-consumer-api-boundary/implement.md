# External ERP Consumer API Boundary Implementation Plan

## Preconditions

- Keep this task in `planning`. Do not run `task.py start`, apply a migration,
  mount an external route, issue a production credential, or enable the feature
  gate until the user reviews these artifacts and explicitly requests
  implementation.
- Before implementation, load `trellis-before-dev` and the current backend
  database, type-safety, error, logging, async-task, and cross-layer specs.
- Reconfirm the current Alembic head, Redis client dependency/API, FastAPI
  mounted-subapplication request-ID behavior, and isolated test database before
  selecting exact migration identifiers or import paths.

## Ordered Checklist

1. Create a bounded `backend/app/modules/external_api/` module with models,
   schemas, service, OAuth dependency, rate limiter, audit middleware, external
   router, protected internal management router, and cleanup task. Reuse the
   existing inventory service only for domain reads; do not expose its DTOs or
   internal routes directly.
2. Add external configuration and a disabled-by-default feature gate. Add
   validation for dedicated JWT/cursor secrets, issuer/audience, 15-minute
   token lifetime, 365-day credential expiry, 24-hour overlap, and a dedicated
   Redis rate-limit URL. Keep the existing SPA JWT configuration untouched.
3. Add database models and an Alembic revision for client/scope/credential,
   30-minute materialized snapshots, and 90-day call audit. Include Chinese
   comments, server-side constraints/indexes, deterministic cleanup, and a
   guarded downgrade that cannot destroy credentials or evidence.
4. Add protected internal client-lifecycle routes and the
   `external_api.clients.manage` permission-catalog/built-in-role migration.
   Return a generated secret only from create/rotate, then prove list/read
   responses cannot return it. Emit D-003 semantic events for lifecycle writes.
5. Implement OAuth2 Client Credentials issuance and external-token validation.
   Validate dedicated JWT claims and current client/credential state on every
   data request. Preserve generic external `401` behavior for unknown,
   inactive, expired, and revoked credentials; return `403` only for valid
   insufficient-scope clients.
6. Implement the Redis Lua token bucket and rate-limit error response. Enforce
   5/minute token issuance, shared 60/minute data rate, 20 burst capacity, and
   maximum 100 records before opening a live inventory query. Treat Redis
   failure as request-correlated `503`.
7. Implement a materialized external snapshot service. It creates the
   allowlisted balance/document projection in one transaction, binds a
   30-minute snapshot to the client, returns signed cursors, and lets later
   pages read only stored snapshot items. Reject a document window over seven
   days and never serialize excluded fields.
8. Mount `/api/external/v1` only when enabled, with its own OpenAPI document
   and matching exception behavior. Add the token, balances, and documents
   contracts; keep all external paths out of the SPA schema/client. Add version
   headers/documentation hooks without changing current `/api/v1` behavior.
9. Implement the independent external audit middleware and direct cleanup task.
   Ensure every final token/data outcome gets one minimal call record, including
   dependency rejections and `429`; audit write failure must release no data.
10. Create integration documentation from the external OpenAPI contract:
    credential onboarding, scopes, pagination/snapshot algorithm, seven-day
    reconciliation, limits, retry/SLA, secret rotation/revocation, 90-day
    deprecation policy, and role-based owner escalation.
11. Add migration, model/service/auth/router/middleware/Redis/task tests and
    execute every case in `e2e-api-tests.md` against an isolated database and
    Redis instance. Regenerate and review the SPA client only for additive
    internal management routes.
12. Run the full quality gate, inspect migration rollback behavior, validate both
    OpenAPI documents, and request the user's implementation approval before
    changing task state.

## Validation Commands

Run only after implementation in a clean isolated environment. Replace the
database and Redis names with task-local test values; never point fixtures at a
development or production database.

```bash
cd backend
EXTERNAL_API_ENABLED=true uv run alembic upgrade head
uv run pytest -q tests/modules/external_api tests/api/routes/test_external_api.py \
  tests/api/routes/test_iam_audit.py tests/modules/inventory
bash scripts/lint.sh

cd ..
bash ./scripts/generate-client.sh
cd frontend
bun run build

cd ..
curl --fail http://127.0.0.1:8000/api/external/v1/openapi.json -o /tmp/external-openapi.json
npx @stoplight/spectral-cli lint /tmp/external-openapi.json -r docs/rules/openapi.spectral.yaml --fail-severity error
git diff --check
```

Then verify the selected isolated backend at
`http://127.0.0.1:8000/api/v1/utils/health-check/`, execute all API cases in
`e2e-api-tests.md`, and confirm the SPA separately at `http://localhost:5173`
if the internal management routes are surfaced there. Run the full backend
suite before deployment and record concrete environment blockers in this file.

## Risk And Rollback Points

- `external_api_credential` and external JWT validation own the next-request
  revocation guarantee. Do not add a cache that lets an old token survive a
  revoke, deactivation, or expired rotation overlap.
- Redis must enforce the rate-limit bucket atomically across workers. An
  in-memory limiter, a non-atomic check/decrement, or fail-open Redis path is
  invalid.
- Offset pagination against live inventory cannot satisfy the complete-window
  reconciliation contract. The stored snapshot must contain only allowlisted
  fields and must bind every cursor to its issuing client.
- A route transaction rolls back on expected errors. The call audit must use an
  independent transaction, preserve `401`/`403`/`429` evidence, and fail closed
  if it cannot do so.
- Do not put external routes in the main SPA OpenAPI document or reuse the SPA
  OAuth dependency/JWT secret. Keep the two trust boundaries distinct.
- Before any downgrade, inspect durable-table counts. A downgrade that drops
  client, credential, or audit data is prohibited while any records exist.

## Activation Gate

- The product owners review `prd.md`, `design.md`, `implement.md`, and
  `e2e-api-tests.md` together.
- Named contacts and support channels are assigned to the role-level owners.
- The actual Redis topology, OpenAPI publication location, and secret-transfer
  channel are approved for the target environment.
- The user explicitly requests implementation. Until then, the task remains
  `planning` and this document authorizes no source, database, deployment, or
  credential change.
