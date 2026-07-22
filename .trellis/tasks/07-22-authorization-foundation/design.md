# RBAC Authorization Foundation Design

## Scope And Boundaries

This task introduces core RBAC for user administration and inventory routes.
It replaces frontend and backend administrator checks based on `is_superuser`
for those surfaces. It does not migrate template Items or the AI inventory
query: `User.is_superuser` remains a backend-only, immutable compatibility
marker for those deferred paths.

RBAC owns functional authorization. The first release grants system-wide
inventory access only; it does not implement organization, row, field, tenant,
or environmental data scopes. The deferred scope is recorded in
[deferred-iterations.md](deferred-iterations.md).

Specifically, a caller with `inventory.documents.manage` may create, update,
delete, and restore every inventory document, including another user's record
and a historical import record. Inventory services must not add creator or
legacy-record predicates in this release, and frontend wording must not imply
an own-record limitation.

Inventory read permissions return the existing full public schema for the
allowed resource. That includes currently exposed creator and updater UUIDs,
import associations, and remarks. No frontend masking or alternate backend DTO
may be presented as a field-security control in this release; field-level
policy remains deferred work.

## Domain Model

### Terms And Invariants

- A Permission is a code-owned, server-verifiable business capability.
- A Role groups Permissions. A User can hold zero or more Roles.
- Effective permissions are the deduplicated union of all active assigned
  Roles. Every protected route is default-deny.
- Built-in Roles have immutable code and baseline permissions. They cannot be
  edited, deactivated, or deleted through the administrator UI or API.
- Custom Roles have immutable unique codes, mutable name and description, and
  are configurable only with catalog Permissions.
- Every `.manage` Permission declares its matching `.read` Permission as an
  explicit prerequisite. Role configuration persists both codes; the runtime
  never infers an unlisted read permission from a manage code.
- The full `system.users.*` and `iam.roles.*` namespaces are Governance
  Permissions and occur only in the built-in `platform_administrator` baseline.
  Custom-role creation and permission replacement reject every code in either
  namespace at the service boundary, regardless of frontend presentation.
- A deactivated custom Role remains assigned but contributes no permissions;
  it cannot receive new assignments. Reactivation makes existing assignments
  effective on the next request.
- Only an inactive, unassigned Custom Role may be deleted.
- The system always retains one active User assigned to the active
  `platform_administrator` Role. Every role-assignment, user-deactivation, or
  user-deletion transaction that could affect this invariant locks the stable
  Platform Administrator Role row first, then counts active assignments and
  verifies the invariant before commit.

### Persistence

Add an `iam` module and durable database objects with the `iam_` namespace.
New independently addressable entities use PostgreSQL `BIGINT GENERATED ALWAYS
AS IDENTITY` identifiers; existing `user.id` references remain UUID.

| Table | Key Fields | Constraints And Ownership |
| --- | --- | --- |
| `iam_permission` | `id`, `code`, `group`, `label`, `description` | `code` unique; catalog rows are migration-seeded and only changed by code-reviewed migrations. |
| `iam_role` | `id`, `code`, `name`, `description`, `is_builtin`, `is_active`, timestamps | `code` unique, lowercase snake_case, immutable at service boundary; built-ins are always active. |
| `iam_role_permission` | `role_id`, `permission_id` | Composite primary key; role-permission membership. |
| `iam_user_role` | `user_id`, `role_id`, `assigned_at` | Composite primary key; preserves assignment across role deactivation. |

The catalog declares prerequisites for `system.users.manage ->
system.users.read`, `system.users.manage -> iam.roles.read`,
`iam.roles.manage -> iam.roles.read`,
`inventory.masters.manage -> inventory.masters.read`, and
`inventory.documents.manage -> inventory.documents.read`. The role service
validates or adds these visible dependencies when creating or replacing a
custom role's permission set; direct persistence bypasses are forbidden.
The same service rejects every Governance Permission in each Custom Role
payload, leaving Custom Roles limited to approved `inventory.*` codes.

Use foreign keys with restrictive deletion for roles and permissions so an
unreviewed delete cannot erase effective access state. User deletion must first
honor the final active Platform Administrator invariant; once permitted, its
role-assignment rows may be removed as part of the same user-deletion
transaction.

Seed the catalog and built-in roles in the Alembic migration. Future catalog
changes occur in new migrations, not admin UI writes. The seed map is:

| Role Code | Assigned Permissions |
| --- | --- |
| `platform_administrator` | Every current catalog permission. |
| `inventory_operator` | Every approved inventory permission in the initial matrix. |
| `inventory_viewer` | `inventory.masters.read`, `inventory.documents.read`, `inventory.balances.read`, `inventory.ledger.read`. |

The migration assigns `platform_administrator` to every existing User whose
legacy `is_superuser` is true. `init_db` must be idempotent: on every startup
it ensures catalog rows, the three built-in roles, their approved baseline
assignments, and the configured first superuser's Platform Administrator
assignment exist. It creates the configured first superuser when absent but
does not assign roles to other normal users or alter Custom Roles. New
registrations and administrator-created users receive no RBAC role by default.

Future permission-catalog migrations must explicitly decide which built-in
roles receive a new permission; no wildcard query may expand a role baseline.
Startup initialization restores only the baseline declared by the current
application catalog; it does not replace custom-role configuration or make a
User a Platform Administrator merely because they were previously assigned an
unrelated role.

After repair, initialization verifies that at least one active User has an
active `platform_administrator` assignment. It must not activate any User or
bypass `is_active` to satisfy this check. When the invariant cannot be met, it
logs a high-priority credential-free diagnostic and aborts startup; an operator
must use the controlled Authorization Recovery procedure to restore a valid
account before restarting.

The administrator-facing user-create DTO accepts an optional list of `role_ids`.
The user service validates role existence and active state, then writes the
User and `iam_user_role` rows atomically. The public registration DTO does not
contain `role_ids`; `extra="forbid"` rejects attempts to add them and successful
registration creates a zero-role User.

## Authorization Flow

```text
Bearer token -> get_current_user -> IAM permission dependency
  -> active user-role assignments -> active roles -> role permissions
  -> allow route/service action or raise PermissionDeniedError (403)
```

The JWT remains an identity token and does not carry permission claims.
Dependencies load current assignment and role state for each protected request,
so role assignments, deactivation, and reactivation take effect on the next
request. The permission dependency lives in `backend/app/modules/iam/` and is
reused by inventory and IAM route handlers; it raises the existing semantic
`PermissionDeniedError` to retain the `detail + request_id` error contract.

Route handlers remain thin. IAM service methods own role lifecycle, assignment
replacement, role deletion, and final-administrator checks; IAM persistence
helpers own query construction. Inventory routes apply the narrow permission
dependency matching the approved matrix before delegating to existing inventory
services. The deferred AI internal routes and template Item services retain
their current authorization behavior.

## API Contract

All new public schemas live under `backend/app/schemas/`; generated frontend
types remain the only API type source. Use the existing `data + count` wrapper
for list responses.

| Endpoint | Permission | Behavior |
| --- | --- | --- |
| `GET /api/v1/iam/me/permissions` | authenticated user | Returns own active role summaries and deduplicated effective permission codes. |
| `GET /api/v1/iam/permissions` | `iam.roles.read` | Returns the read-only, grouped permission catalog. |
| `GET /api/v1/iam/roles` | `iam.roles.read` | Lists built-in and custom roles with status and assigned permission codes. |
| `POST /api/v1/iam/roles` | `iam.roles.manage` | Creates a custom role with a unique immutable code and selected catalog permissions. |
| `PATCH /api/v1/iam/roles/{role_id}` | `iam.roles.manage` | Updates mutable custom-role fields, including activation state. |
| `PUT /api/v1/iam/roles/{role_id}/permissions` | `iam.roles.manage` | Replaces a custom role's catalog permission set. |
| `DELETE /api/v1/iam/roles/{role_id}` | `iam.roles.manage` | Deletes only an inactive, unassigned custom role. |
| `PUT /api/v1/iam/users/{user_id}/roles` | `system.users.manage` | Replaces a user's role assignments after active-role and final-administrator validation. |

Existing `/api/v1/users/*` routes move from the superuser dependency to
`system.users.read` or `system.users.manage` as appropriate. User public and
admin DTOs expose assigned Role summaries needed for the UI, but do not expose
the legacy `is_superuser` marker. The ORM field stays on `User` rather than the
shared public user schema so legacy backend-only Items and AI code can continue
to read it.

`POST /api/v1/users/` accepts an administrator-create schema with optional
`role_ids` and requires `system.users.manage`. `POST /api/v1/users/signup`
continues using its public registration schema, rejects `role_ids`, and creates
no assignment.

`system.users.manage` has `iam.roles.read` as a catalog prerequisite, letting
user-management roles load role summaries for assignment without granting
`iam.roles.manage` or access to role mutation endpoints.

Invalid input remains `422`; duplicate role codes and lifecycle conflicts use
the existing conflict semantics; missing resources are `404`; authenticated
callers lacking a permission receive `403` with `detail` and `request_id`.

## Frontend Design

`useAuth` continues to own current-user session behavior. A focused IAM query
loads `GET /iam/me/permissions`; shared permission helpers consume its typed
effective permission set rather than `is_superuser`.

- Replace `canAccessAdmin` with a narrow `hasPermission` helper.
- Route guards accept required permission codes. They keep login routing
  separate from authorization routing.
- Add a protected forbidden route/page for authenticated callers. Guards for
  `/admin/*` and `/inventory/*` send unauthorized direct visits there with a
  return destination; the page does not require a business permission. The
  destination is an internal `pathname + search` value only if it begins with
  `/` and not `//`; both guard and page validate it, and invalid/missing values
  return to `/`.
- Permission guard state is explicit: while `GET /iam/me/permissions` is
  pending, wait behind a controlled loading state; `401` follows the existing
  token-expiry login flow; an unexpected `403` is a configuration/error state;
  network or `5xx` failures render a retryable general error state; only a
  successful response missing the required code renders the forbidden page.
- Filter `menu-config.ts` entries by required permission. Existing Items and
  Rules entries remain outside this migration; inventory entries map to the
  corresponding read permission.
- Keep `/admin` as the user-management route and add `/admin/roles` as a thin
  route to a platform/system role-management page. The user page uses a
  multi-select role assignment control and removes the superuser checkbox.
- The role page uses the generated IAM client, grouped read-only permission
  catalog, visible prerequisite selection, and custom-role lifecycle controls.
  Built-in role controls are inspection-only. The custom-role editor displays
  the complete catalog, marks every Governance Permission as unavailable with
  a "Built-in Platform Administrator only" explanation, and permits only
  `inventory.*` selection; server validation remains decisive.
- Inventory pages use permission checks for create/edit/delete/restore and
  suggestion actions, while their route access requires the corresponding read
  permission. No frontend condition replaces backend enforcement.

The raw-material ledger and finished-shipment pages share
`inventory.documents.read` and `inventory.documents.manage`. No document-type
specific permissions are introduced in this release; a holder of the pair may
access both pages and their backing document endpoint subject to the approved
system-wide inventory scope.

`inventory.balances.read` remains independent from `inventory.ledger.read`.
The balances page renders balance data for a balances-only role, but hides the
clickable related-ledger interaction and drawer unless the effective permission
set includes ledger read. The ledger route/API still independently requires
`inventory.ledger.read`; no absent drawer is an authorization mechanism.

Any schema change triggers `bash ./scripts/generate-client.sh`; generated
client and route-tree files are never edited manually.

The forbidden-page return parameter must never accept a complete URL,
protocol-relative path, `javascript:` value, or other external target. It is a
navigation safety boundary, not merely a UI convenience.

## Security, Operations, And Rollback

Role codes, permissions, and role assignments are authorization metadata, not
secrets. Do not log passwords, tokens, or AI actor grants. This task does not
introduce a durable access or configuration audit log; its capture, retention,
and query policy remain D-003 work in the parent backlog.

Authorization Recovery is an operational runbook concern for this task: record
the exact database-level remediation separately from application logs, restrict
it to authorized operators, and never place raw passwords, tokens, or personal
data in the diagnostic output.

The database migration is additive: it creates IAM tables, seeds catalog data,
and backfills roles without removing `User.is_superuser`. A backend rollback
can therefore continue legacy Items and AI behavior. Deploy the regenerated
frontend and RBAC-capable backend as one compatible release because the new
frontend requires IAM endpoints and removes the legacy admin flag. Database
rollback is limited to a pre-release environment; production recovery should
roll back application code while retaining RBAC rows until their state is
reviewed.

## Validation Shape

Backend tests cover permission calculation, catalog and built-in protections,
inactive-role semantics, final-administrator concurrency, every allowed/denied
inventory route class, and legacy Items/AI compatibility. Frontend checks cover
menu filtering, direct forbidden routing, role-assignment UI, role lifecycle
controls, and disabled inventory actions. The detailed API scenarios are in
[e2e-api-tests.md](e2e-api-tests.md).
