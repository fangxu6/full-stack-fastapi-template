# Inventory Exception Correction Design

## Boundary

This is one inventory workflow, not a reusable workflow runtime. It adds only
the storage needed to keep an approved proposal separate from its automatic
application. The executor recognizes one fixed handler type:
`inventory.document_correction`.

## Flow

```text
ledger-affected inventory document
  -> immutable correction request
  -> review decision
  -> independent application work item
  -> existing scheduler scans and claims it
  -> inventory correction transaction
  -> succeeded or terminal failed
```

The request creation and approval path never changes inventory. The executor
is the only path that may call the existing inventory write service for an
eligible document.

## Direct Write Gate

The existing document service is the shared guard point because the ordinary
routes are its only current callers. Eligibility means a non-legacy document
whose current lines have at least one ledger entry, including a soft-deleted
ledger entry. Ordinary update, delete, and restore reject an eligible document
with the existing unified HTTP 409 body whose `detail` is
`INVENTORY_CORRECTION_REQUIRED`.

All expected correction conflicts use the existing semantic error pipeline:
the response body contains both `detail` and `request_id`, and the response
contains the matching `X-Request-ID` header. No route-local error shape is
introduced.

The executor calls one inventory-local `apply_approved_correction(...)` path,
which validates a locked work item before delegating to the existing write
logic. It does not expose a public `bypass` flag. This keeps create, import,
negative-balance, and ledger code in one place.

The existing document page adds a `纠错` action for callers with request
permission and opens the correction page with the document ID. If an ordinary
action receives this 409, it uses the same navigation. No `requires_correction`
field is added to the public document schema.

## Minimal Persistence

### Correction request

The database namespace is `inventory_correction`. The three durable tables are
`inventory_correction_request`, `inventory_correction_work_item`, and
`inventory_correction_attempt`; their indexes, constraints, foreign keys,
sequences, and Alembic description use the same prefix. Each table has a
BIGINT generated-always identity, `AuditFields`, PostgreSQL Chinese table and
column comments, and no delete path.

One request row stores the document reference, operation, expected `updated_at`,
immutable proposal JSON, proposal hash, reason, reviewer, decision time, and
request status. The audit creator is the initiator. The request body is a
closed Pydantic model with `extra="forbid"` at both the request and nested
proposal boundaries: `UPDATE_DOCUMENT` requires one `InventoryDocumentCreate`;
delete and restore require no proposal. `reason` is trimmed, nonblank, and
bounded to 500 characters, while `expected_updated_at` must be timezone-aware.
The hash input is a typed object containing the target ID, operation,
UTC-normalized expected timestamp, normalized proposal (or `null`), and
normalized reason. Its `model_dump(mode="json")` is canonically JSON-serialized
with sorted keys and compact separators, then SHA-256 hashed before persistence.
There is no revision or attachment table.

One partial unique constraint permits only one request in `PENDING_REVIEW` or
`APPROVED` for a document. A request becomes `APPLICATION_FAILED` after a
terminal application failure, allowing a changed proposal to create a new
request. Request transitions are protected with a row lock.

Recovery locks the terminal request and checks for another active request for
the same document before changing it back to `APPROVED`. If one exists, it
raises the stable `INVENTORY_CORRECTION_ACTIVE_REQUEST` conflict and leaves the
request, work item, and attempts unchanged. Concurrent request creation catches
the partial-unique `IntegrityError` and maps it to the same 409 contract.

Approval-time staleness is a committed terminal decision, not an exception
after mutation: the service marks the request `STALE`, creates no work item,
and returns the normal typed request response. Only request precondition or
authorization failures use the unified error response.

| Current state | Allowed result | Condition |
| --- | --- | --- |
| `PENDING_REVIEW` | `APPROVED` | Reviewer approves a current target |
| `PENDING_REVIEW` | `REJECTED` | Reviewer rejects |
| `PENDING_REVIEW` | `WITHDRAWN` | Initiator withdraws |
| `PENDING_REVIEW` | `STALE` | Approval sees a changed `updated_at`; the committed decision response carries `STALE` |
| `APPROVED` | `APPLIED` | Work item succeeds |
| `APPROVED` | `APPLICATION_FAILED` | Work item is terminal |
| `APPLICATION_FAILED` | `APPROVED` | Authorized recovery queues a next attempt |

### Correction work item

One `inventory_correction_work_item` row has a unique request ID, target ID,
expected timestamp, proposal hash and snapshot, fixed handler type, current
status, lease expiry, current attempt sequence, and terminal failure category.
Queue selection uses an explicit pending-status/creation-time index. The
handler has a fixed-value check for `inventory.document_correction`; there is
no generic handler configuration or executable class path.

### Application attempt

Approval creates the first `PENDING` attempt. Recovery creates exactly one next
`PENDING` attempt with a unique `(work_item_id, sequence)` and a
`RECOVERY` origin. The scheduler claims that row, fills its scheduler-run ID,
and changes it to `RUNNING`; it does not insert an attempt. `AuditFields`
retain the reviewer or recovery user as creator and the System Actor as the
application updater. A terminal row is never edited or deleted.

No attempt row has a foreign key to `SchedulerRun`: scheduler runs expire after
90 days while correction history must remain readable.

Persisted operation, request status, work-item status, attempt status, attempt
origin, and failure category are separate named PostgreSQL `StrEnum` types
under the `inventory_correction_*` namespace. Public schemas reuse those enum
types; the migration creates types before tables and drops them after dependent
tables during an empty-table downgrade. It does not use text status checks.

## Concurrency And Application

`updated_at` is the optimistic-concurrency token; no new document version
column is needed. Add it to the public document response and serialize it in
the correction request. Creation rejects a stale token. Approval rechecks it.

HTTP mutation routes use `AuditedWriteSessionDep` and never commit directly;
the request unit of work owns commit/rollback. The scheduler task opens its own
short-lived `Session`, binds `context.actor_id` (the System Actor for this
bootstrap job) before any audited flush, and clears it in `finally`. Celery
continues to carry only the durable scheduler run ID.

The executor opens one audited write transaction, locks the work item and
document, rechecks the token and status, and invokes the existing inventory
write operation. The document/ledger mutation, attempt outcome, work-item
status, request status, and successful-application audit event commit together.
This leaves no post-commit window in which a committed ledger effect is not
marked successful.

Negative-balance and domain validation failures roll back the inventory change,
then record `TERMINAL_FAILED` in a separate short transaction. `STALE_TARGET`,
`NEGATIVE_BALANCE`, `EXECUTION_LOST`, and `EXECUTION_FAILED` are stable MVP
categories; exception text is not persisted.

## Scheduler

Add one bootstrap-managed inventory scheduled task that scans a bounded batch
of 20 `APPROVED_PENDING_APPLY` work items with a `PENDING` attempt. Add the
idempotent tuple `inventory.document_correction.apply` to
`INVENTORY_BOOTSTRAP_JOBS`, with the fixed display name
`Inventory document correction application`, class path
`app.modules.inventory.scheduled_tasks.InventoryCorrectionApplyTask`, empty
`ScheduledTaskConfig`, and cron `* * * * *`; the class sets both
`allow_run_now` and `allow_backfill` to `False`. It uses the existing scheduler
task base and runs as the System Actor. A `SchedulerRun` represents the scan
batch, not one work item.

Claiming locks the pre-created attempt and creates a work-item lease. If a
worker dies before the application transaction commits, a later scan marks the
expired claim
`TERMINAL_FAILED/EXECUTION_LOST`; it does not apply it again. If the transaction
commits, the status is already `SUCCEEDED`, so a repeated delivery exits without
effect. This preserves no automatic retry while tolerating at-least-once task
delivery.

Recovery locks a terminal work item, verifies the document timestamp and
proposal hash, confirms that no other active request exists for the same
document, appends the next attempt, changes the work item to pending, and
returns `202`. An active-request conflict returns the stable 409 without any
state or attempt change. The next scan performs the application as the System
Actor.
An item-level domain failure is finalized in its own short transaction and the
scan continues with later items. Only an unhandled scan failure marks the
`SchedulerRun` failed.

## Authorization And UI

Use three new permissions, with `inventory.documents.read` as the existing
read prerequisite:

| Permission | Allowed actions |
| --- | --- |
| `inventory.corrections.request` | Create, list own requests, withdraw pending request |
| `inventory.corrections.review` | View review queue, approve or reject |
| `inventory.corrections.recover` | View terminal queue and recover |

No permission implies a distinct person. Seed request permission to the
Inventory Operator and all three permissions to Platform Administrator; custom
roles may combine them.

The route and menu use the shared prerequisite `inventory.documents.read`, so
no any-permission navigation helper is needed. The page renders only the tabs
for its correction permissions. Its backend access matrix is strict:

- request permission: create, own list/detail, and own pending withdrawal;
- review permission: review queue, pending detail, approval, and rejection;
- recovery permission: terminal queue, terminal detail, and recovery.

All queue data is filtered server-side. One inventory-correction route owns the
three permission-filtered tabs and detail view. It shows business rows, not raw
`AuditEvent` records. There is no manual apply control.

## API

- `POST /api/v1/inventory/correction-requests`: create one submitted request.
- `GET /api/v1/inventory/correction-requests/mine`: requester's own history.
- `GET /api/v1/inventory/correction-requests/review-queue`: review queue.
- `GET /api/v1/inventory/correction-requests/{id}`: authorized detail.
- `POST /api/v1/inventory/correction-requests/{id}/approve`, `/reject`, and
  `/withdraw`: empty-body state actions.
- `GET /api/v1/inventory/correction-work-items/recovery-queue`: terminal
  work-item queue.
- `POST /api/v1/inventory/correction-work-items/{id}/recover`: empty-body
  recovery; there is deliberately no apply endpoint.

Every queue endpoint accepts `skip >= 0` and `1 <= limit <= 100`, returns
`{ data, count }`, and orders by `created_at DESC, id DESC`. The page keeps
one-based pagination state and uses the generated client.

## Audit And Logs

Use explicit correction action codes and fixed summary keys for creation,
approval, rejection, withdrawal, and successful application. Failure evidence
lives in the attempt row. The inventory correction service owns the fixed
`AuditEvent` action/summary mapping; summaries may contain only operation,
target document ID, proposal hash, work-item ID, and attempt sequence. They
never contain raw JSON proposal, reason, exception text, or actor identity.
Existing Celery lifecycle telemetry is sufficient; this task does not extend
the closed task-log allowlist or emit correction resource IDs to stdout.

## Migration And Rollback

The migration is additive: the three namespaced tables, named enum types,
JSON-object checks, target/request/attempt uniqueness, and queue indexes. It
does not add a document version column, audit-reader API,
scheduled-job-per-work-item table, or dependency.

Downgrade is supported only while all three new tables are empty. Once a
correction exists, recovery is a forward migration or database restore, so its
history is not silently discarded.

Future generic handlers, external effects, and notifications remain explicitly
deferred in [deferred-iterations.md](./deferred-iterations.md).
