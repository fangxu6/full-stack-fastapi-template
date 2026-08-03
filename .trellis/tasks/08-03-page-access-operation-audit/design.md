# IAM audit vertical slice design

## Scope and decisions

This design implements only the IAM administration slice approved in
`prd.md`: the protected users and roles pages, their successful entries and
frontend/backend denial outcomes, role mutations, permission replacement, and
user-role replacement. Scheduler and inventory events are not part of this
task.

The audit record is an immutable evidence row, not a replacement for
operational logs or model audit fields. The API exposes query results only to
the built-in `Platform Administrator` role. There is no export endpoint.

## Boundaries and data flow

### Event writer

Add a typed audit writer under `backend/app/modules/audit/` and an
`AuditEvent` model under `backend/app/models/audit.py`. All writer entry points
accept a typed event command and enforce the page, operation, resource, result,
and change-summary allowlists. Actor identity is resolved from the authenticated
request or server-side task context; no request body can supply an actor email,
raw payload, or arbitrary actor UUID.

The target table inventory, logical relationships, deliberate foreign-key
omissions, indexes, and migration order are recorded in
[`database-relationships.md`](database-relationships.md).

The event table uses the stable `audit_` domain prefix. Its PostgreSQL enum
types and matching Python `StrEnum` contracts are:

- `audit_event_type`: `page_access`, `authorization`,
  `privileged_operation`.
- `audit_event_source`: `frontend_route_guard`, `backend_permission`,
  `backend_operation`.
- `audit_event_outcome`: `succeeded`, `denied`, `failed`.
- `audit_event_result_code`: `success`, `permission_denied`,
  `frontend_guard_denied`, `validation_failed`, `conflict`,
  `transaction_failed`.
- `audit_page_code`: `iam_users`, `iam_roles`.
- `audit_operation_code`: `iam_role_create`, `iam_role_update`,
  `iam_role_permissions_replace`, `iam_role_delete`,
  `iam_user_roles_replace`.
- `audit_resource_type`: `iam_page`, `iam_role`, `iam_user`.
- `audit_actor_kind`: `anonymous`, `user`, `system`.

The event table has a generated `BIGINT` identity `id`, UTC `occurred_at`,
nullable `actor_user_id` (UUID), `actor_kind`, event/source/outcome enums,
nullable page, permission, operation, resource type and resource ID fields,
nullable request ID, nullable result code, and nullable JSONB
`change_summary`. Events do not carry `created_by` / `updated_by` fields and
are never updated.

`actor_user_id` and resource identifiers intentionally have no foreign-key
delete dependency. This preserves an identifier-only historical row when a
user or role is deleted. The trade-off is that current display names must be
resolved opportunistically by the query service; an absent related row is
shown as a deleted/unknown identifier.

Use explicitly named indexes for time ordering and the query filters:
`ix_audit_event_occurred_at`, `ix_audit_event_actor_time`,
`ix_audit_event_resource_time`, and `ix_audit_event_type_outcome_time`.
Every table, enum, index, and constraint receives the required Chinese
database comments in the Alembic revision.

### Page access and denial capture

1. Add `POST /api/v1/audit/events/page-access`. The authenticated user is
   taken from `CurrentUser`; the body contains only an allowlisted page code
   and outcome. The backend maps each page code to its required permission and
   rejects unknown page codes with the shared validation contract. A
   `succeeded` submission is accepted only after the backend rechecks the
   mapped permission; a `denied` submission is stored as browser-reported
   evidence and is never promoted to an authoritative backend denial.
2. `requirePermission()` reports a denied `iam_users` or `iam_roles` guard
   event before redirecting to `/forbidden`. The call is fire-and-forget and
   must not block navigation or turn an audit outage into a user-facing error.
3. The IAM page components report a successful entry once after the page is
   mounted. A small in-memory navigation key prevents duplicate events from a
   single route transition.
4. Extend `permission_required()` with the request context needed to record
   the route template, permission code, and actor before re-raising
   `PermissionDeniedError`. This writer uses an independent short-lived
   session, so the authoritative backend denial survives the request rollback.
   Unauthenticated denials use `actor_kind=anonymous` and a null actor UUID.

Frontend events are explicitly labeled as browser-reported evidence. The
backend event is authoritative for authorization and is never inferred from a
frontend payload.

### Privileged operation capture

Define one operation specification per IAM mutation and route the service call
through a shared `run_audited_operation()` helper. The helper:

- validates the operation/resource contract before invoking the service;
- writes a success event to the same `WriteSessionDep` transaction after the
  service returns, so the event and committed IAM change are atomic;
- catches expected validation and conflict exceptions, maps them to a stable
  result code, writes a failure event through a new independent session, then
  re-raises the original application error;
- catches unexpected transaction failures only to record
  `transaction_failed` with no input summary, then re-raises;
- never serializes the request body. Success summaries are constructed from
  allowlisted scalar fields and IDs after the service has validated them.

The helper covers role create/update/deactivation/delete, role permission
replacement, and user-role replacement. Permission checks remain separate, so
a denied request produces a `backend_permission` authorization event rather
than a privileged-operation failure event.

### Query and UI

Add `GET /api/v1/audit/events` with bounded pagination and filters for event
type, source, outcome, actor UUID, operation, resource type/ID, permission,
and an inclusive UTC time window. The response contains only the typed public
fields and the whitelist change summary. There is no bulk endpoint and no
export format.

Protect the query dependency with a small
`platform_administrator_required()` check against the existing role code; do
not add an `audit.read` permission in this slice. Add an `/admin/audit` page
and a route guard that checks the current effective roles for
`platform_administrator`. Render a dense, paginated table with event time,
source, outcome, operation/page, resource identifier, actor UUID, result code,
and the redacted summary. Missing current users/roles remain visible by ID.

After backend schemas change, regenerate the frontend client with the existing
repository script and keep the generated diff limited to the audit contract.

### Retention and cleanup

Implement `cleanup_expired_events(now)` as an idempotent service operation that
deletes rows with `occurred_at < now - 365 days` in bounded batches and returns
the deleted count. Register a no-credential `AuditRetentionTask` with the
existing scheduler task contract and a daily default job owned by the System
Actor. The service remains directly callable for deterministic tests and an
operations runbook; cleanup failure must be observable but must not delete
newer rows.

## Migration and rollback

The forward Alembic revision creates the enum types before `audit_event`, then
indexes and comments. The downgrade refuses while any audit rows remain; only
an empty table may be dropped, followed by its enum types. This prevents a
rollback from silently destroying evidence. Retention cleanup is the explicit
data-deletion path.

Deployment order is migration, backend writer/query/capture, generated client,
then frontend route/page. Rollback of an application release leaves the table
and events in place. A schema rollback requires an empty-table check and a
reviewed backup/restore decision.

## Risks and mitigations

- A browser can forge its own page event. Keep source and actor binding
  server-controlled, rate-limit the endpoint, and never use browser events as
  authorization proof.
- A failed operation can outlive the business transaction only through the
  independent writer. Add failure-path tests that assert the event remains
  after rollback.
- Free-text or future enum drift can leak data or break migrations. Enforce
  Python and PostgreSQL enums, whitelist summaries, and add forward-only enum
  migration tests.
- Audit insertion must not make a successful IAM change fail unexpectedly.
  Treat same-transaction success insertion as mandatory evidence; surface a
  clear application error and rollback if it cannot be persisted.

## Acceptance mapping

The implementation must prove the PRD acceptance items through the API/UI E2E
cases in `e2e-api-tests.md`, migration tests, writer unit tests, frontend guard
tests, and the isolated backend quality gate.
