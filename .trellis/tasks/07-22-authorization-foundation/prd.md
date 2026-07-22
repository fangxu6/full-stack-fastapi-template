# Plan RBAC authorization foundation

## Goal

Design and plan a mainstream role-based access control (RBAC) foundation for
the platform. The result must give later platform capabilities a consistent
actor, role, permission, resource, and action contract while preserving the
current FastAPI, React, PostgreSQL, generated OpenAPI-client, and private
AI-sidecar boundaries.

## Confirmed Context

- This is D-001, the first child of the enterprise platform capability
  backlog. It must be planned and delivered independently before later
  observability, auditing, scheduler, external API, MCP, or workflow work
  depends on it.
- Current authorization is only partial: administrator guards and resource
  ownership checks exist, but there is no role-permission-resource model or
  granular page, control, and API authorization.
- RBAC must begin with concrete business roles and protected resources; a
  generic permission matrix without a first use case is not sufficient.
- Credentials, tokens, audit data, and AI-tool inputs are sensitive. The
  design must define data minimization, retention, access, and redaction
  rules before storing or exposing them.
- Authentication is Bearer-token based. `User` currently exposes only
  `is_active` and `is_superuser`; backend access is split between a
  superuser dependency and service-level ownership checks.
- The active inventory module is the first substantial business surface, but
  its API endpoints currently require only an authenticated user. Template
  items retain owner-or-superuser behavior, while rule documents are readable
  by any authenticated user and the AI inventory query requires a superuser.
- Frontend administration, route guarding, and menu visibility all currently
  derive from the same `is_superuser` value. Existing platform guidance
  reserves `GET /api/v1/iam/me/permissions` and role-management endpoints as
  the target RBAC contract.
- The provided RBAC reference and its source distinguish functional
  permissions from data scope. It supports many-to-many user-role and
  role-permission assignments, least privilege, default deny, and
  server-enforced authorization.
- The current platform has no organization, department, position, role
  hierarchy, field-classification, or managed data-scope model. Inventory
  records already have processing-unit and creator references, but no current
  business rule establishes a role-specific row-level boundary.

## Requirements

1. Establish a least-privilege RBAC model that supports platform users,
   roles, permissions, protected resources, and actions.
2. Define the initial business use case, roles, resources, action vocabulary,
   and authorization behavior for denied requests before selecting the final
   permission matrix.
3. Preserve existing administrator and ownership behavior through an explicit
   compatibility and migration plan; do not silently broaden access.
4. Apply authorization consistently at backend API boundaries and frontend
   navigation/control presentation. Frontend checks must not be the only
   enforcement point.
5. Produce a cross-layer design, implementation plan, migration/rollback
   plan, and API-level validation plan before implementation may start.
6. The first release must govern the inventory business surface, including
   master data, inventory documents, ledger, and balances. It must define
   permissions for read and management actions, and it must not rely on
   frontend checks as enforcement.
7. Seed and support these initial business roles:
   - Platform Administrator: manages users, roles, and permissions and has
     every inventory permission.
   - Inventory Operator: manages inventory master data and documents and may
     read ledger and balances.
   - Inventory Viewer: may only read inventory master data, documents, ledger,
     and balances.
8. Preserve current template-item and AI inventory-query authorization during
   this release. Retain `is_superuser` as an immutable, backend-only
   compatibility marker for those deferred paths. New users and role
   assignments must not write it, and the management UI must not expose a
   mutable superuser control.
9. A user may hold multiple roles. Effective permissions are the union of all
   active assigned-role permissions; absence of a matching permission denies
   access. The system must preserve at least one active Platform Administrator.
10. Treat the first release as system-wide inventory access. It must not claim
    organization, department, owner-row, field-level, or contextual access
    control that the platform cannot yet model and test. A user with
    `inventory.documents.manage` may manage every inventory document,
    including records created by other users and historical import records.
    Inventory read permissions return the current complete inventory API field
    set, including creator/updater identifiers, import associations, and
    remarks; this release has no field-level redaction.
11. Use stable, server-verifiable permission codes as the authorization
    contract. Menu, route, and button visibility may consume the effective
    permission set but must not define authorization truth.
12. Seed the three initial roles as protected built-in roles with stable codes
    and a non-removable minimum permission baseline. Platform Administrators
    may create, edit, activate, deactivate, and delete custom roles and assign
    only permissions from the system-owned catalog. They may not create
    arbitrary permission codes or delete or recode built-in roles.
13. During migration, assign the Platform Administrator role to every existing
    `is_superuser` account. Replace the user-management interface's
    `is_superuser` toggle with multiple-role assignment; the resulting RBAC
    permissions become the authorization source for user administration and
    inventory access.
14. A caller holding the user-management permission may assign, replace, or
    remove any built-in or custom role for any user, including the Platform
    Administrator role. Do not add approval, role hierarchy, or
    separation-of-duty behavior in this release. In the same transaction, the
    service must reject deleting, deactivating, or removing the Platform
    Administrator role from the last active Platform Administrator.
15. Keep the existing user-management surface under `/admin` and replace its
    superuser toggle with multiple-role assignment. Add a separate protected
    role-management page under `/admin` for listing, creating, editing,
    activating, deactivating, and deleting custom roles and selecting their
    permissions from a read-only, grouped permission catalog. Do not create a
    runtime permission-catalog management surface.
16. Preserve user-role assignments when a custom role is deactivated, but
    exclude inactive roles from effective-permission calculation and reject new
    assignments to them. Re-enabling a role restores its existing assignments.
    Authorization must evaluate current user, role, and assignment state on
    each request so changes take effect on the next request.
17. Permit deletion only for custom roles that are inactive and have no
    user-role assignments. Built-in roles cannot be deleted. The API and UI
    must explain which prerequisite blocks a requested deletion.
18. Require a unique lowercase `snake_case` code for every role. Role codes
    are immutable after creation; display names and descriptions remain
    editable. The built-in codes are `platform_administrator`,
    `inventory_operator`, and `inventory_viewer`.
19. Assign no RBAC role automatically to self-registered or
    administrator-created users. A zero-role user may authenticate and use
    personal-account flows but cannot access RBAC-governed inventory or
    administration capabilities until a Platform Administrator explicitly
    assigns an active role.
20. Hide unauthorized menu entries. A direct authenticated browser visit to an
    `/admin/*` or `/inventory/*` route without its required permission must
    render a dedicated forbidden page with a return action, rather than silently
    redirecting to the dashboard. Protected API requests return `403` through
    the existing `detail + request_id` error contract.
21. Model each `.manage` permission as an explicit permission-catalog
    dependency on its corresponding `.read` permission. Role editing must add
    the prerequisite visibly, and the service must reject a permission set
    that omits it; authorization must not infer unlisted permissions at
    runtime.
22. Extend the `system.users.manage`-protected administrator `POST /users`
    contract with optional `role_ids`. Validate the selected active roles and
    create the user plus its role assignments in one transaction. Public
    self-registration must not accept role identifiers and always creates a
    zero-role user.
23. Declare `iam.roles.read` as an additional explicit prerequisite of
    `system.users.manage`, so a user-management role can load assignable role
    summaries without gaining `iam.roles.manage`.
24. Reserve the full `system.users.*` and `iam.roles.*` Governance Permission
    namespaces for the built-in `platform_administrator` role. Reject any
    custom-role create or permission-replacement request containing a code in
    either namespace; do not rely on UI filtering. Custom roles may therefore
    combine only approved `inventory.*` permissions in this release.
25. Make startup initialization idempotently ensure the system-owned permission
    catalog, built-in roles, and their approved baseline assignments exist, and
    ensure the configured `FIRST_SUPERUSER` holds the
    `platform_administrator` role. It must not assign roles to other normal
    users or overwrite custom-role configuration.
26. Startup initialization must never reactivate a user or bypass inactive-user
    checks. If no active Platform Administrator exists after idempotent repair,
    it must log a high-priority, credential-free diagnostic and fail startup;
    recovery requires a controlled operational database procedure followed by
    restart.
27. The forbidden-page return target must accept only an internal relative path
    beginning with `/` but not `//`. Missing or invalid values fall back to
    `/`; complete URLs, protocol-relative URLs, `javascript:` values, and every
    external target are forbidden. Guards pass the original internal
    pathname/search value, and the page validates it again before navigation.
28. Distinguish authorization-query states in the frontend. While effective
    permissions are loading, guards wait and render a controlled loading state.
    A `401` follows the existing login-expiry flow; a `403` from the own
    permissions endpoint is an implementation/configuration error; network or
    `5xx` failures render a retryable error page; only a successful permission
    response that lacks the required code renders the forbidden page.
29. Keep raw-material ledger and finished-shipment document pages under the
    shared `inventory.documents.read` and `inventory.documents.manage`
    permissions; do not create document-type-specific permissions in this
    release. In the custom-role editor, display the complete grouped catalog
    but show every `system.users.*` and `iam.roles.*` permission as disabled
    with the explanation that it is available only to the built-in Platform
    Administrator role.
30. Keep `inventory.balances.read` independent of `inventory.ledger.read`. On
    the balances page, hide row-click behavior and the related-ledger drawer
    when the user lacks ledger read permission; show both only when the user
    has both permissions. The ledger API remains independently protected.

## Initial Permission Matrix

| Permission Code | Protected Capability | Platform Administrator | Inventory Operator | Inventory Viewer |
| --- | --- | --- | --- | --- |
| `system.users.read` | List and inspect users | Yes | No | No |
| `system.users.manage` | Create, edit, deactivate, delete users and assign roles | Yes | No | No |
| `iam.roles.read` | List and inspect roles and their assigned permissions | Yes | No | No |
| `iam.roles.manage` | Create, edit, deactivate, delete custom roles and configure their permissions | Yes | No | No |
| `inventory.masters.read` | List processing and receiving units | Yes | Yes | Yes |
| `inventory.masters.manage` | Create and update processing and receiving units | Yes | Yes | No |
| `inventory.documents.read` | List and inspect inventory documents | Yes | Yes | Yes |
| `inventory.documents.manage` | Create, update, delete, restore documents, and use editor suggestions | Yes | Yes | No |
| `inventory.balances.read` | Read raw and finished inventory balances | Yes | Yes | Yes |
| `inventory.ledger.read` | Read inventory ledger entries | Yes | Yes | Yes |

The Platform Administrator has every permission in this table. Inventory
Operator has every approved inventory permission in this table. Inventory
Viewer has the four inventory read permissions. Future permission codes do not
silently expand a built-in role; each catalog expansion requires an explicit
migration and role-baseline decision. Permission codes represent stable
business capabilities; individual HTTP methods, routes, menu entries, and
buttons do not become independently configurable permissions.

## Acceptance Criteria

- [ ] The initial business use case and its testable acceptance criteria are
  approved by the product owner.
- [ ] The planned RBAC model defines actors, roles, permissions, resources,
  actions, assignment rules, and the default-deny behavior.
- [ ] The three approved initial roles produce the approved inventory access
  behavior: administrator has all actions, operator has inventory management
  plus read access, and viewer has read-only access.
- [ ] Effective permissions are the deduplicated union of a user's active role
  assignments, and unassigned permissions receive a backend `403` response
  using the existing `detail + request_id` error contract.
- [ ] Built-in role codes and their minimum permission baseline are protected,
  while Platform Administrators can manage custom roles only through the
  system-owned permission catalog.
- [ ] Every pre-existing superuser has the Platform Administrator role after
  migration, and user creation/editing uses role assignments instead of a
  superuser boolean.
- [ ] The user-management interface cannot create or alter `is_superuser`,
  while existing Items and AI authorization behavior remains unchanged through
  the retained compatibility marker.
- [ ] Role assignment, user deletion, and user deactivation reject any request
  that would leave no active Platform Administrator, including concurrent
  requests targeting the final administrator.
- [ ] Backend routes, frontend route guards, menu items, and actionable
  controls use only the approved permission matrix and agree on its allowed
  and denied behavior.
- [ ] Platform Administrators can complete user-role assignment and custom-role
  management through protected `/admin` pages without a mutable superuser or
  permission-catalog UI.
- [ ] Deactivating an assigned custom role removes its permissions on the next
  request without deleting its assignments, and reactivation restores the
  same effective permissions.
- [ ] A custom role cannot be deleted while active or assigned, and no delete
  operation cascades silently into user-role removal.
- [ ] Role codes are unique and immutable, while role names and descriptions
  are editable without changing machine references.
- [ ] Newly created and self-registered zero-role users are denied all
  RBAC-governed inventory and administration actions until an active role is
  assigned.
- [ ] An Inventory Operator can create, update, delete, and restore any
  inventory document in the system, including other-user and historical import
  records, while a Viewer cannot mutate any of them.
- [ ] A Viewer permitted to read inventory data receives the current complete
  API field set without frontend-only or backend field redaction.
- [ ] Unauthorized menu entries are hidden; direct unauthorized route visits
  render the forbidden page; and protected API calls return `403` with
  `detail` and `request_id`.
- [ ] Every role containing a `.manage` permission also persists the matching
  `.read` permission, and invalid configurations are rejected without changing
  the role's prior permission set.
- [ ] A failed administrator user-create request with `role_ids` creates no
  user or assignments, while public self-registration rejects supplied roles
  and creates a zero-role user on success.
- [ ] A role holding `system.users.manage` also has `system.users.read` and
  `iam.roles.read`, but does not gain role-configuration access unless it is
  separately assigned `iam.roles.manage`.
- [ ] A custom-role write containing any `system.users.*` or `iam.roles.*`
  code is rejected transactionally and cannot expose global users, role
  configuration, or self-service governance escalation.
- [ ] Re-running startup initialization repairs missing catalog or built-in-role
  baseline rows and the configured first-superuser assignment without changing
  custom roles or assigning any normal user a role.
- [ ] Startup fails without reactivating any user when no active Platform
  Administrator exists after repair, and logs actionable recovery context
  without credentials, tokens, or personal data.
- [ ] Forbidden-page navigation accepts only validated internal relative return
  paths and falls back to `/` for missing, malformed, protocol-relative, or
  external targets.
- [ ] Permission-query loading, `401`, unexpected `403`, network/`5xx`, and a
  successful missing-permission response render their distinct approved
  frontend outcomes without exposing a protected page.
- [ ] One `inventory.documents.*` permission pair governs both raw-material and
  finished-shipment document pages; the custom-role editor visibly disables
  Governance Permissions while the API rejects their submission.
- [ ] A balances-only role can view balances without calling or exposing the
  ledger drawer, while a role with both read permissions can open and read the
  related ledger; the ledger API independently rejects callers without
  `inventory.ledger.read`.
- [ ] The design maps every initially protected API and frontend surface to
  its required permission, including the administrator and ownership
  compatibility rules.
- [ ] The design defines migrations, seed/bootstrap behavior, rollback, and
  a strategy for safe permission changes in production.
- [ ] The plan covers backend enforcement, generated-client compatibility,
  frontend behavior, automated tests, and API E2E cases for allowed and
  denied access.

## Out of Scope

- Implementing D-002 through D-007 or creating further child tasks.
- Replacing authentication, exposing private AI-sidecar capabilities, or
  designing an external-consumer API authorization product.
- Migrating template items, rule documents, or AI inventory queries to the new
  permission model.
- Organization, department, position, role-hierarchy, static/dynamic
  separation-of-duty, row-level, field-level, environmental, and tenant-level
  access policies; see [deferred-iterations.md](deferred-iterations.md).

## Open Questions

None. The PRD is ready for technical design and implementation planning.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
