# RBAC Review Findings API E2E Test Plan

## Environment

- Backend test database: `POSTGRES_DB=aiadmin_test` or another database ending
  in `_test` / `_pytest`.
- The pytest fixture upgrades that isolated database to Alembic head before
  RBAC bootstrap.
- Browser target: the local frontend with an isolated backend when exercising
  guard outcomes.

## Cases

| ID | Flow | Setup | Request / Action | Expected Result |
| --- | --- | --- | --- | --- |
| E2E-001 | Test bootstrap | Isolated database behind the prior IAM migration | Direct focused `uv run pytest` | Migration runs before bootstrap and IAM tests execute rather than fail on missing tables. |
| E2E-002 | Retained inactive Role | User assigned a custom role, then role deactivated | Replace role IDs with the same inactive ID | `200`; assignment remains and contributes no effective permission. |
| E2E-003 | New inactive Role rejection | User without that inactive role | Replace role IDs with the inactive ID | `409`; existing assignments remain unchanged. |
| E2E-004 | Last administrator invariant | Only one active Platform Administrator | Remove its platform role while retaining other role state | `409`; administrator assignment remains. |
| E2E-005 | Permission query failures | Authenticated browser and mocked `/iam/me/permissions` failure modes | Direct navigation to a protected inventory/admin route | `401` clears the invalid token and goes to login; `403` renders `/forbidden?reason=configuration`; network/`5xx` renders `/forbidden?reason=retry`; retry returns to the requested protected path; missing permission uses the default forbidden state. |

## Execution Record

Executed on 2026-07-23 against `POSTGRES_DB=aiadmin_test`.

| ID | Result | Evidence |
| --- | --- | --- |
| E2E-001 | Passed | Direct `uv run pytest tests/modules/iam/test_iam_service.py tests/api/routes/test_users.py tests/api/routes/test_inventory.py -q` upgraded the isolated database and completed with `55 passed`. |
| E2E-002 | Passed | `test_replace_user_roles_retains_existing_inactive_role` preserves the assignment while the inactive role contributes no effective permission. |
| E2E-003 | Passed | `test_replace_user_roles_rejects_new_inactive_role` receives `ConflictError` and leaves the user's assignments empty. |
| E2E-004 | Passed | `test_cannot_remove_last_active_platform_administrator` remains green in the focused IAM service suite. |
| E2E-005 | Passed | `bunx playwright test tests/permission-guards.spec.ts --no-deps --project=chromium --workers=1` passed six cases covering 401 token clearing/login, configuration and retry reasons on the existing forbidden route, retry navigation, and default forbidden state. |

Additional gates: backend lint, the generated-client normalization test,
frontend guard unit tests, frontend Biome CI, and
`bunx tsc --noEmit -p tsconfig.build.json` passed. `bun run build` was
intentionally not used after the route refactor because the route topology is
unchanged and the no-write TypeScript check avoids rewriting generated output.
