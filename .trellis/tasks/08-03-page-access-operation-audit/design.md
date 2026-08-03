# IAM semantic change audit design

## Scope and decisions

This task implements one reusable, database-backed semantic change table and
the first IAM writer slice. It records only successful role and user-role
changes. There is no page-access collection, authorization-denial capture,
failure event, audit API, reader UI, export, generic database trigger, or
external audit service.

An audit row is application-append-only evidence, not a replacement for
operational logs or entity audit fields. It is not tamper-proof against a
database owner or administrator; that threat model requires a separately
approved database-privilege or external-sink design.

## Event table

Add `AuditEvent` under `backend/app/models/audit.py` and one `audit_event`
table. The table is generic because its `action` and `resource_type` are stable
namespaced identifiers owned by application code, not IAM-specific columns.
They are text rather than PostgreSQL enums because new modules will introduce
new action vocabulary; they are not user-managed business states.

| Column | Type | Null | Contract |
| --- | --- | --- | --- |
| `id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | No | Immutable event identifier. |
| `occurred_at` | `TIMESTAMPTZ` | No | UTC event time, defaulted by the server. |
| `actor_user_id` | `UUID` | Yes | Authenticated actor UUID; no FK so history survives user deletion. |
| `request_id` | `TEXT` | Yes | Server-derived HTTP correlation ID; null for a future non-HTTP writer. |
| `action` | `VARCHAR(128)` | No | Stable code such as `iam.role.permissions_replaced`. |
| `resource_type` | `VARCHAR(64)` | No | Stable code such as `iam_role` or `iam_user`. |
| `resource_id` | `VARCHAR(128)` | No | Primary resource ID encoded as text for mixed UUID/BIGINT resources. |
| `changes` | `JSONB` | No | Object containing only the action's allowlisted summary. |

The migration adds Chinese comments to the table and every physical column.
It adds `CHECK (jsonb_typeof(changes) = 'object')` plus these indexes:

- `ix_audit_event_occurred_at (occurred_at DESC)` for retention and timeline
  inspection.
- `ix_audit_event_resource_time (resource_type, resource_id, occurred_at DESC)`
  for resource investigation.
- `ix_audit_event_actor_time (actor_user_id, occurred_at DESC)` for actor
  investigation.

There are no foreign keys from `audit_event` to mutable IAM data. The row has
no `updated_at`, soft-delete, or update endpoint. The normal application role
writes and retention deletes it; this is the explicit application-level
immutability boundary.

## Writer and transaction boundary

`backend/app/modules/audit/` owns a small `append_audit_event()` service. It
accepts an already validated action, resource, actor UUID, server request ID,
and changes object; it rejects a non-object summary and does not accept a
request body or actor identity from a client.

Each IAM mutation route obtains `CurrentUser` and the middleware-owned request
ID, then invokes the existing IAM service with that server-resolved context.
The IAM service reads any allowlisted before state it needs and adds one event
through the same `WriteSessionDep` session. `WriteSessionDep` commits after the
route returns, so the IAM change and audit row commit or roll back together.
The writer does not catch or independently persist failed mutations. Existing
exception handling and request-correlated logs remain responsible for those
failures.

The first action vocabulary is:

| Action | Primary resource | Allowed `changes` |
| --- | --- | --- |
| `iam.role.created` | `iam_role` / new role ID | `code`, `permission_codes` |
| `iam.role.updated` | `iam_role` / role ID | `changed_fields` for a general update without a state transition |
| `iam.role.activated` | `iam_role` / role ID | `is_active: {before: false, after: true}` and optional non-state `changed_fields` |
| `iam.role.deactivated` | `iam_role` / role ID | `is_active: {before: true, after: false}` and optional non-state `changed_fields` |
| `iam.role.permissions_replaced` | `iam_role` / role ID | `permission_codes: {before, after}` |
| `iam.role.deleted` | `iam_role` / role ID | `{}` |
| `iam.user.roles_replaced` | `iam_user` / user UUID | `role_ids: {before, after}` |

The IAM action/resource/change-summary allowlist is enforced in the IAM service
next to its action construction, with focused tests. The generic writer accepts
only an object summary and no client payload. A future module adds its own
action strings and allowlisted summary without changing the table or adding a
generic framework.

## Retention

`cleanup_expired_events(session, now)` deletes rows where
`occurred_at < now - 365 days` and returns the deleted count. A direct
`audit.cleanup_events` Celery Beat task invokes it once daily, following the
existing direct scheduler-run cleanup pattern. It is not registered as a
`SchedulerJob`, does not have a UI, and has no configuration or credentials.

## Migration and rollback

The Alembic revision creates `audit_event`, its check constraint, indexes, and
required comments. It does not create PostgreSQL enum types. An application
rollback leaves the table and recorded events intact. A schema downgrade refuses
when rows exist and drops the table only after an explicit empty-table check;
it never silently destroys audit evidence.

## Deferred scope

The table and writer are deliberately reusable, but reusable storage is not an
authorization to collect every event. The deferred page, denial, failure,
reader, trigger, and tamper-resistance capabilities are listed in
[`deferred-iterations.md`](deferred-iterations.md). Each needs its own task and
acceptance criteria before implementation.
