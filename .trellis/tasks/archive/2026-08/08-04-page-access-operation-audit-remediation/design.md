# IAM audit remediation design

## Scope

This remediation preserves the existing IAM routes, `audit_event` schema, and
action vocabulary. It corrects two behaviors in the role-mutation service:

1. Concurrent writes to one role must not interleave permission-link changes
   or produce stale audit snapshots.
2. Empty or same-value role PATCH requests must return the unified 422 error
   contract before any persistence or audit side effect.

User-role replacement, audit reading, retention, and database-trigger-level
protection remain outside this task.

## Role write serialization

Extend `repository.get_role_by_id()` with `lock: bool = False`. The default
path retains `Session.get()` for all current readers. The locked path issues a
`SELECT ... FOR UPDATE` for the requested role row.

`update_role()`, `replace_role_permissions()`, and `delete_role()` use the
locked read before examining the role, reading old permission links, or
performing validation based on current state. Role creation does not lock
because it has no existing row.

The shared `WriteSessionDep` already owns one PostgreSQL transaction and
commits after the route returns. A row lock is held from the service read until
that commit or an exception-triggered rollback. With PostgreSQL's normal
read-committed behavior, a waiting request resumes from the current committed
role state, then reads the correct association rows before it replaces them.

For example, a first transaction replaces `[P1]` with `[P2]`. A concurrent
second transaction waits at the role lock; after the first commits, it reads
`[P2]`, replaces it with `[P3]`, and records `before=[P2], after=[P3]`. The
final set is `[P3]`, not an interleaved union. The lock is an application
service boundary: direct SQL outside that boundary is intentionally not
covered.

## No-op PATCH contract

Add an IAM-local `AppError` subclass with status 422 and a stable detail such
as `Role update does not change any fields`. It uses the existing global
handler, so the response remains `{detail, request_id}` and has
`X-Request-ID`.

After reading the locked role, `update_role()` compares every supplied field
with its current stored value. It constructs a new update dictionary containing
only fields whose values actually differ. When that dictionary is empty,
raise the 422 error before setting `updated_at`, adding the role to the
session, flushing, or appending an audit event.

Real updates use only that actual-change dictionary. This keeps
`changed_fields` truthful and preserves state-event handling: a real
`is_active` transition records its precise boolean before/after pair, while
mixed updates add only the truly changed non-state fields.

## Compatibility and failure behavior

- Endpoint paths, request shape, success response shape, action codes, and
  audit retention remain unchanged.
- Empty and same-value PATCH requests change from a successful no-op to a
  unified 422 response. No database migration or frontend-client generation is
  needed because the project already exposes the shared 422 error contract.
- A lock wait, database error, or domain error follows the existing request
  Unit of Work rollback behavior. No audit event survives a failed request.

## Test design

Use the isolated PostgreSQL test database and two independent `Session`
instances to hold the role lock in one transaction while the second service
call attempts a permission replacement. Assert that the second call completes
only after the first commit, that its event's `before` set is the first
transaction's committed set, and that the final links equal only the second
request's set.

API tests cover empty and same-value role PATCHes. Each asserts 422,
`request_id` propagation, unchanged `updated_at`, and unchanged audit-event
count. A real PATCH remains a 200 response with one expected semantic event.
