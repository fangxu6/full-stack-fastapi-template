# RBAC Authorization Foundation Implementation Plan

## Preconditions

- Keep this task in planning until all artifacts are reviewed and the user
  explicitly approves `task.py start`.
- Preserve the parent backlog boundaries in `deferred-iterations.md`.
- Do not manually modify generated frontend API client or route-tree output.

## Implementation Order

1. Add the IAM domain model and schemas.
   - Create `backend/app/modules/iam/` for router, service, repository, and
     authorization dependencies.
   - Add SQLModel entities for permissions, roles, and both associations;
     export them from `backend/app/models/__init__.py` for Alembic discovery.
   - Add typed request/response schemas for role summaries, role CRUD,
     catalog entries, user-role replacement, and effective permissions.

2. Create the Alembic migration and safe bootstrap path.
   - Create namespaced IAM tables, unique constraints, indexes, and restrictive
     foreign keys.
   - Seed all approved permission codes and the three protected built-in roles.
   - Backfill every existing `is_superuser` User to `platform_administrator`.
   - Update startup initialization to idempotently repair catalog and built-in
     baselines and ensure the configured first superuser has the seeded platform
     role, without assigning roles to other normal users or altering custom
     roles.
   - Verify post-repair active Platform Administrator availability; log a
     credential-free high-priority diagnostic and abort startup if none exists,
     without reactivating any account.

3. Implement authorization and IAM lifecycle services.
   - Query effective permissions from active assignments and roles per request.
   - Add a typed permission dependency that raises `PermissionDeniedError`.
   - Enforce immutable catalog and built-in role protections, custom-role code
     validation, explicit manage/read prerequisites, Governance Permission
     exclusion, inactive-role assignment rejection, and delete prerequisites.
   - Implement user-role replacement, role deactivation/reactivation, user
     deactivation/deletion, and role assignment with transactional
     final-active-administrator protection.

4. Expose IAM and migrate user administration.
   - Register the IAM router in the API assembly.
   - Implement the planned IAM endpoints and route responses.
   - Replace superuser dependencies on user-administration routes with the
     approved `system.users.*` permissions.
   - Extend administrator user creation with optional `role_ids`, writing the
     user and validated active-role assignments atomically; keep public signup
     role-free and reject extra role input.
   - Remove `is_superuser` from user API DTOs and user-management request
     payloads while retaining it on the ORM model for deferred code paths.

5. Protect inventory API routes.
   - Apply the approved `inventory.*` permission dependencies to each read and
     management endpoint without moving business rules into route handlers.
   - Keep inventory service behavior and data scope system-wide for this task.
   - Confirm template Item and AI routes still use their intentional legacy
     authorization behavior.

6. Regenerate the frontend API client and implement permission presentation.
   - Run `bash ./scripts/generate-client.sh` after public schemas settle.
   - Replace boolean admin helpers with effective-permission helpers and an IAM
     permission query.
   - Add guards and the forbidden page with validated internal return targets;
     align every inventory and admin route with its read permission.
   - Model pending, `401`, unexpected `403`, network/`5xx`, and
     missing-permission states distinctly so only a successful authorization
     result may render the forbidden page.
   - Filter menu entries centrally and condition inventory mutation controls.
   - Update the existing admin user page for role assignment and build the
     role-management page under `platform/system` with thin route entries.
     Display Governance Permissions as disabled explanatory catalog entries;
     keep both document pages mapped to the shared document permission pair.
   - Keep balances read independent of ledger read; hide balances row-detail
     entry and drawer unless the user has `inventory.ledger.read`.

7. Add focused automated coverage and execute the quality gate.
   - Add IAM model/service/API tests and adapt user, inventory, and frontend
     tests from `is_superuser` assertions to permission scenarios.
   - Run the API E2E plan in `e2e-api-tests.md` against an isolated database.
   - Run backend lint and focused/full tests, frontend generation/lint/build,
     and relevant Playwright tests.

## Risk And Rollback Points

| Point | Risk | Required Control | Rollback Shape |
| --- | --- | --- | --- |
| IAM migration | Backfill or seed error locks out administrators. | Assert role seed and superuser assignment in migration tests before deployment. | Restore database backup in pre-release; production app rollback retains additive IAM rows for inspection. |
| Startup recovery | A partial seed leaves the configured bootstrap administrator locked out. | Make catalog/built-in/first-superuser repair idempotent and test repeat startup. | Re-run the deterministic initializer after correcting the failed deployment. |
| Administrator loss | All Platform Administrators are inactive or unassigned. | Fail startup after credential-free diagnostic; never auto-reactivate. | Authorized operator executes the documented Authorization Recovery procedure, then restarts. |
| Role-write service | Concurrent final-admin changes leave zero active administrators. | Lock and re-count active platform assignments in one transaction. | Roll back failed transaction; do not cascade assignments. |
| Custom role write | A delegated custom role can self-escalate to platform governance. | Reject Governance Permissions at the IAM service boundary and cover bypass attempts in API tests. | Failed transaction leaves prior role state unchanged. |
| User DTO change | Old frontend expects `is_superuser`. | Regenerate client and release the new frontend with the RBAC backend. | Revert application release while legacy DB field remains. |
| User creation | A partial create leaves an unintended zero-role account. | Validate role IDs and commit user plus assignments in one transaction. | Roll back the transaction; no user or assignment rows persist. |
| Inventory route guards | A missing or wrong permission causes exposure or outage. | Route-by-route allow/deny tests plus frontend menu/guard verification. | Revert backend/frontend release; database state stays additive. |
| Forbidden return path | A crafted target redirects users outside the application. | Validate only `/`-prefixed, non-`//` internal paths in both guard and page. | Invalid or absent target falls back to `/`. |
| Permission query | A loading or unavailable authorization source is mistaken for denial or access. | Keep explicit pending, login-expiry, error, and successful-denial states. | Retry transient failures; only successful missing permission reaches forbidden UI. |
| Role deactivation | Unexpectedly removes assignments or stale access persists. | Test inactive-role query behavior on each request. | Reactivate role to restore preserved assignments. |

## Validation Commands

Run from the repository root unless stated otherwise:

```bash
bash backend/scripts/lint.sh
cd backend && uv run pytest tests/api tests/modules
bash ./scripts/generate-client.sh
cd frontend && bun run build
cd frontend && bunx playwright test
```

`bun run lint` may write unsafe Biome fixes; inspect its diff before retaining
any output. Use the isolated test environment named in the E2E plan before
calling local API cases complete.

## Review Gate Before Start

- [ ] PRD convergence pass completed with no unresolved questions.
- [ ] Design and implementation artifacts agree on role lifecycle, catalog,
  permission matrix, API contracts, compatibility, and rollback.
- [ ] E2E cases cover successful and denied API behavior plus unchanged state.
- [ ] The user has reviewed the planning artifacts and explicitly approved
  implementation.
