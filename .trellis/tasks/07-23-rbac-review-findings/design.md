# RBAC Review Findings Repair Design

## Boundaries

The repair keeps the existing FastAPI -> SQLModel -> PostgreSQL authorization
flow and React route guard boundary. It changes no permission codes, built-in
role baselines, or public role lifecycle API.

## Backend Quality And Test Bootstrap

Use SQLModel's configuration type for schemas that need `extra="forbid"`,
and give the dependency factory a concrete callable return type. This keeps
mypy strict rather than papering over errors with checker-specific ignores.

The session-scoped pytest fixture already rejects unsafe database names. After
that guard, it will programmatically run Alembic to `head`, then call
`init_db`. The migration is idempotent, so an already-upgraded isolated test
database remains valid. Production startup and its migration runner stay
unchanged.

## Inactive Role Replacement

`replace_user_roles` will load the target user's current role IDs before
validating the desired role set. A desired inactive Role is valid only when it
was already assigned to that same user; this is a retention no-op, not a new
assignment. Every other inactive Role remains a conflict. The existing role
row lock and final active Platform Administrator count remain in the same
transaction.

This fixes the user-editor failure without creating a second combined update
endpoint. A concurrent lifecycle change may still make a later request fail,
but the deterministic inactive-role preservation path succeeds.

## Frontend Guard Outcomes

Extract a small pure guard-error classifier. The guard continues to redirect a
`401` to login after clearing the invalid persisted token. It redirects an
own-permissions `403` and all network/`5xx` failures to the existing
authenticated `/forbidden` route with a validated
internal return route and a `reason` search parameter. Its app-level page
implementation renders the configuration or retryable error state and retries
by navigating back to that return route; only a successful permission response
that lacks the requested Permission uses the default forbidden state. No new
route topology is introduced, so the generated route tree remains unchanged.

## Generated Client Hygiene

Add a repository-owned normalization helper and invoke it from
`scripts/generate-client.sh` immediately after `openapi-ts`. The helper strips
only trailing spaces/tabs from generated TypeScript files, leaves semantic
content untouched, and allows the normal generation path to satisfy
`git diff --check` without manual generated-file edits.

## Frontend Policy Deletions

The frontend component policy resolves each changed source path before
evaluating protected-path and component-root rules. A path that no longer
exists is a deletion, so it has no component content to validate and is
skipped. Existing paths keep the current strict generated-file, placement,
Ant Design, and shared-import checks. The existing `frontend/src/routes` root
is allowed only for thin route entries; a route entry that declares a
PascalCase component remains a policy violation.

## Rollback

Revert this repair commit to restore the prior behavior. The migration remains
unchanged; test-bootstrap migration execution has no production runtime path.
