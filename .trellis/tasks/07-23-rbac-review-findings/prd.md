# Fix RBAC Review Findings

## Goal

Repair the quality, test-bootstrap, RBAC role-lifecycle, frontend
authorization-error, and generated-client hygiene regressions found in the
review of `22ea2172`. This is a repair child of the enterprise capability
backlog, not an expansion of the D-001 permission matrix.

## Confirmed Findings

- `bash backend/scripts/lint.sh` fails mypy because new SQLModel schemas use a
  Pydantic `ConfigDict` incompatible with SQLModel's declared configuration
  type, and `permission_required` has an untyped return.
- A direct backend test run against the isolated `aiadmin_test` database fails
  before test collection because its fixture calls RBAC bootstrap before the
  new IAM migration has created the IAM tables. Production prestart upgrades
  migrations, but the test path does not.
- A deactivated custom Role keeps its existing assignments by design. The
  user editor sends those retained inactive IDs back to `replace_user_roles`,
  which rejects all inactive IDs. The user update has already been committed
  when that second request fails.
- Permission-route guards only redirect a `401`; own-permissions `403` and
  network/`5xx` failures fall through to an undifferentiated router error,
  contrary to the D-001 contract.
- Generated SDK output contains trailing whitespace that Biome intentionally
  ignores under `frontend/src/client`, so `git diff --check` fails.
- The frontend component policy evaluates deleted `.tsx` paths before checking
  whether they still exist, so removing a noncompliant temporary route can
  itself fail the quality gate.

## Requirements

1. Restore a clean backend static-analysis gate without weakening strict mypy
   or removing input `extra="forbid"` behavior.
2. Make a direct `uv run pytest` test invocation bootstrap an isolated test
   database at Alembic head before RBAC initialization. It must retain the
   existing `_test` / `_pytest` database safety check and never upgrade a
   production-like database.
3. Preserve an already-assigned inactive Role when replacing a user's role
   set, but continue rejecting a newly added inactive Role. This repair must
   preserve the last-active-Platform-Administrator invariant.
4. Classify own-permissions query failures at the route guard: `401` follows
   session-expiry login behavior, `403` renders an authenticated configuration
   error, and network/`5xx` errors render a retryable error. A successful
   response lacking the requested Permission continues to render forbidden.
5. Make generated-client whitespace normalization part of the repository
   generation pipeline; do not hand-edit generated client artifacts.
6. Skip deleted frontend paths in the component policy while preserving all
   checks for paths that still exist, including the thin-route restriction.

## Acceptance Criteria

- [ ] `bash backend/scripts/lint.sh` passes with no new suppressions that hide
  the reviewed type errors.
- [ ] A direct focused pytest invocation on an isolated, pre-migration test
  database reaches and executes RBAC tests after upgrading to head.
- [ ] Retained inactive role assignments do not block an otherwise valid user
  edit or role-replacement request; an inactive role that was not already
  assigned remains rejected.
- [ ] The final active Platform Administrator cannot be removed while
  repairing retained inactive-role behavior.
- [ ] Frontend guards expose distinct login, configuration-error, retryable
  error, and forbidden outcomes, with a retry action that returns to the
  original internal route.
- [ ] The client generator pipeline removes trailing spaces/tabs from generated
  TypeScript and `git diff --check` passes after regeneration.
- [ ] Backend targeted tests, frontend unit/type checks, and the task E2E plan
  pass against an isolated environment.

## Out of Scope

- Altering D-001 roles, permission codes, governance-permission policy, or
  deferred Items and AI compatibility behavior.
- Introducing a new combined user-and-role update API contract.
- Implementing D-002 observability, D-003 audit, or any later parent-backlog
  capability.
