# Fix IAM audit concurrency and no-op events

## Goal

Correct the IAM semantic-audit regressions found in `b3cf2bb`: role writes
must serialize the state used as audit evidence, and role PATCH requests that
make no semantic change must fail clearly instead of emitting a false event.

## Requirements

1. Serialize IAM mutations for one existing role before the service reads its
   current state, rewrites its permission links, or builds an audit summary.
   Concurrent permission replacements must leave exactly the permission set
   requested by the transaction that acquires the lock next; their audit
   `before` and `after` lists must describe the actual committed transition.
2. An empty role PATCH, or a PATCH whose supplied values all equal the stored
   role values, returns the shared HTTP 422 contract. It must not change
   `updated_at`, write an `AuditEvent`, or commit any business mutation.
3. A PATCH with at least one real field change retains the existing response
   shape and writes exactly one allowlisted IAM audit event. A state transition
   continues to record exact boolean `before` and `after` values.
4. Keep the existing database schema, IAM endpoint paths, action vocabulary,
   request-ID propagation, and audit retention behavior unchanged.

## Acceptance Criteria

- [x] Two independent sessions cannot interleave a role-permission replacement
  into a mixed final permission set; the second request observes the first
  committed set as its audit `before` value.
- [x] Empty and same-value `PATCH /api/v1/iam/roles/{role_id}` requests return
  422 with `detail`, `request_id`, and `X-Request-ID`, while preserving the
  role row and leaving audit-event count unchanged.
- [x] A real role PATCH still succeeds and writes one correct semantic event.
- [x] Existing IAM mutation, audit, and focused Celery registration tests pass
  against an isolated test database, together with the backend lint gate.

## Notes

- This remediation is limited to existing role mutations. It does not add an
  audit reader, change user-role replacement semantics, or introduce a new
  database migration.
