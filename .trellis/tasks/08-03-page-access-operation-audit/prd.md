# Page-access and operation audit

## Goal

D-003 plans durable, queryable evidence for the first selected protected page
accesses, denied authorization attempts, and privileged business operations.
It must answer who performed or attempted which action against which resource,
when it occurred, and whether it succeeded. It is distinct from operational
observability and from entity `created_by` / `updated_by` attribution.

## Confirmed Context

- D-001 RBAC and D-002 structured observability are completed parent
  capabilities. D-003 depends on their actor, permission, and request-context
  contracts.
- The current `backend/app/modules/audit` package is a skeleton. It has no
  event store, capture boundary, query API, or reader-facing UI.
- Frontend page guards enforce `requirePermission()` before protected-route
  entry and redirect missing permissions to `/forbidden`
  (`frontend/src/app/router/guards.ts:38`). This is a browser-side decision;
  it produces no durable page-access or denial record.
- Backend protected routes use `permission_required()` to call
  `service.require_permission()` (`backend/app/modules/iam/dependencies.py:8`,
  `backend/app/modules/iam/service.py:85`). A failed check raises
  `PermissionDeniedError`.
- The exception handler emits only the operational `authorization.denied`
  event with `actor_kind` and an authorization result
  (`backend/app/core/exceptions.py:169`). `log_event()` has no durable actor
  identifier, permission code, resource identifier, request payload, or event
  store (`backend/app/core/observability.py:149`). It cannot satisfy an audit
  reader or evidence-retention requirement.
- `AuditedWriteSessionDep` binds the current user for SQLAlchemy audit-field
  stamping (`backend/app/api/deps.py:20`); the `before_flush` hook writes only
  entity `created_by` / `updated_by` fields
  (`backend/app/core/audit.py:103`). It does not record page views, denied
  access, semantic operation names, deleted-resource evidence, or a query
  trail.
- The selected first audit surface is IAM administration. It includes the
  role-management page and user-management access boundary, their successful
  entries and denied outcomes, and role creation, update, deactivation,
  deletion, permission replacement, and user-role replacement
  (`frontend/src/platform/system/pages/AdminRolesPage.tsx:33`,
  `frontend/src/platform/system/pages/AdminUsersPage.tsx:41`, and
  `backend/app/modules/iam/router.py:49`).
- Scheduler job management (`backend/app/modules/scheduler/router.py:73`) and
  all inventory pages and operations remain deferred. They may reuse the
  approved audit contract only in a separately reviewed follow-up scope.
- V1 captures both frontend route-guard denials and backend permission denials.
  Frontend records represent browser-reported access attempts; backend records
  represent authoritative authorization outcomes. The event contract and query
  UI must expose their distinct evidence sources.
- V1 records one outcome event for every selected privileged operation. A
  committed change has outcome `succeeded`; an authorized attempt that fails
  validation, conflict checks, or transaction completion has outcome `failed`.
  Failed-operation records contain only the operation, resource identifier,
  and result code, never the rejected input.

## Requirements

1. Deliver the IAM-administration vertical slice: successful protected-page
   entries, frontend and backend denied-access outcomes, and the listed role
   and user-role management operations. Its purpose is to investigate access
   and authorization changes that alter another user's effective permissions.
2. Define a durable event contract with actor identity, timestamp, event type,
   evidence source, authorization outcome, permission/action, resource type
   and identifier, request correlation, outcome, result code, and a redacted
   change summary only for committed changes.
3. Define data minimization, redaction, retention, reader authorization,
   export restrictions, and the failed-authorization capture policy before
   choosing storage or collection mechanics.
4. Design capture, query API, and UI boundaries without treating request logs
   or model audit fields as audit records. The design must cover frontend page
   entry separately from backend API authorization and write operations.

## Access Policy

- V1 audit queries are read-only and available only to users assigned the
  built-in `Platform Administrator` role. The first release introduces no
  separate audit-reader role or permission.
- V1 provides no audit-record export. A later export proposal must define its
  authorization, data minimization, and traceability requirements separately.

## Retention Policy

- IAM audit records are retained for 365 days from their event timestamp, then
  permanently deleted. The first implementation must provide a deterministic,
  testable cleanup mechanism and must not rely on best-effort log rotation.
- Extending retention, placing records on legal hold, or restoring expired
  records is out of scope for V1 and requires a separate approved policy.

## Data Minimization and Redaction

- V1 persists only stable user UUIDs, role IDs and codes, event and permission
  codes, resource identifiers, request correlation, and a whitelisted change
  summary. It must not persist email addresses, full names, passwords, tokens,
  complete request or response bodies, or free-text role descriptions.
- The change summary may name the changed field and record allowed scalar
  values such as `is_active`, role IDs, and permission codes. It must omit
  unapproved fields rather than serializing an input model generically.
- The audit query UI may resolve a current display name outside the audit
  record, but the durable event remains identifier-only and must stay readable
  after its related user or role is deleted.

## Acceptance Criteria

- [x] Product owner approves the IAM-administration interaction set and its
  operational purpose.
- [x] V1 audit reading is restricted to `Platform Administrator`; export is
  explicitly excluded.
- [x] IAM audit records are retained for 365 days and then permanently deleted.
- [x] V1 uses identifier-only audit records and a whitelist-based change
  summary; it excludes PII, credentials, raw payloads, and free-text role
  descriptions.
- [x] PRD defines reader roles, retention, redaction, export restrictions, and
  the policy for both frontend and backend failed authorization.
- [x] Privileged-operation events distinguish committed success from authorized
  failure; failed records retain no rejected input.
- [ ] The approved event contract distinguishes page entry, authorization
  outcome, and privileged-operation evidence and names the actor/resource
  fields required for each.
- [ ] Design, implementation plan, migration/rollback plan, and validation
  scope are reviewed before `task.py start`.

## Out of Scope

- Implementing the audit module or activating this task before the listed
  product decisions are made.
- Treating operational logs or model audit fields as a substitute for durable,
  reader-authorized audit evidence.
- Scheduler and inventory audit collection in the IAM MVP.
