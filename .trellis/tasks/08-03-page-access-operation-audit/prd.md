# Semantic change audit

## Goal

D-003 plans durable, reusable evidence for successful high-value state changes.
The first slice records IAM role and role-assignment changes so an internal
operator can answer who changed which permission-bearing resource and when.
It is distinct from operational observability and from entity `created_by` /
`updated_by` attribution.

## Confirmed Context

- D-001 RBAC and D-002 structured observability are completed parent
  capabilities. D-003 depends on their actor, permission, and request-context
  contracts.
- The current `backend/app/modules/audit` package is a skeleton. It has no
  event store or shared semantic-change writer.
- `WriteSessionDep` owns the request transaction and commits only after the
  route returns (`backend/app/api/dependencies/database.py:15`). An audit row
  added to that session is therefore atomic with a successful IAM mutation.
- The IAM mutation surface is role creation, update (including activation or
  deactivation), permission replacement, deletion, and user-role replacement
  (`backend/app/modules/iam/router.py:32`).
- Request correlation is already generated server-side and exposed as
  `request.state.request_id` and `X-Request-ID`
  (`backend/app/core/exceptions.py:80`). It is safe to copy into an audit row;
  it is not supplied by a request body.
- Existing frontend route guards, authorization-denied logs, and entity audit
  fields are useful for navigation, operational debugging, and row attribution,
  but none provides a reusable semantic change history.
- Scheduler and inventory changes are deferred. They may reuse the table and
  writer only after an independent task defines their action codes and allowed
  change summaries.

## Requirements

1. Deliver the IAM semantic-change vertical slice for successful role and
   user-role mutations. Every committed mutation writes exactly one durable
   event in the same transaction.
2. Introduce one reusable `audit_event` table with actor identity, occurrence
   time, server-supplied request correlation, namespaced action, primary
   resource identity, and an allowlisted JSONB change summary.
3. Define data minimization and 365-day retention for the table. The table is
   application-append-only: this task introduces no update/delete API and no
   claim of protection from a database owner or administrator.
4. Keep the writer generic but the event vocabulary domain-owned. New modules
   reuse the table and writer while defining their own stable action codes and
   per-action change-summary allowlists.

## Reader Policy

- V1 exposes no audit query endpoint, UI, or export. Existing privileged
  database operations are the only reader path; this task does not add a
  database role, grant, or application reader permission.
- A future reader surface must define its own authorization, pagination,
  redaction, and export policy before it is implemented.

## Retention Policy

- Audit events are retained for 365 days from their event timestamp, then
  permanently deleted by a deterministic direct Celery Beat task. This is not
  a user-managed scheduler job and does not rely on log rotation.
- Extending retention, placing records on legal hold, or restoring expired
  records is out of scope for V1 and requires a separate approved policy.

## Data Minimization and Redaction

- V1 persists only actor UUID, stable IAM action/resource identifiers,
  server-supplied request correlation, and a whitelisted change summary. It
  must not persist email addresses, full names, passwords, tokens, complete
  request or response bodies, role descriptions, or arbitrary old/new rows.
- The change summary records only approved fields. IAM role creation records
  its code and permission codes; activation changes record `is_active`;
  permission and user-role replacements record before/after identifier lists.
  A display-name change records only that `name` changed, not its free text.

## Acceptance Criteria

- [x] Product owner approves the IAM mutation set and its operational purpose.
- [x] V1 has no audit API, reader UI, or export.
- [x] IAM audit records are retained for 365 days and then permanently deleted.
- [x] V1 uses identifier-only audit records and a whitelist-based change
  summary; it excludes PII, credentials, raw payloads, and free-text role
  descriptions.
- [x] V1 records committed success only; failed and denied attempts remain
  outside the table.
- [x] The approved event contract names the actor, request, action, resource,
  and allowed change fields for every IAM mutation.
- [x] Design, implementation plan, migration/rollback plan, and validation
  scope are reviewed before `task.py start`.

## Out of Scope

- Implementing the audit module or activating this task before the listed
  product decisions are made.
- Capturing page entries, frontend or backend authorization denials, failed
  mutations, or raw database row snapshots.
- Adding a query API, audit UI, export, database trigger, separate database
  role, or tamper-resistant audit sink.
- Scheduler and inventory audit collection in the IAM MVP. See
  [deferred-iterations.md](deferred-iterations.md) for the confirmed follow-up
  boundaries.
