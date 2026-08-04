# Inventory exception correction

## Goal

Provide the smallest controlled path for correcting a saved inventory document
that has already affected the ledger. The flow must prevent approval bypass,
keep the ledger consistent, and leave enough durable evidence to investigate a
correction later. It is a concrete prerequisite for D-007, not a workflow
platform.

## Confirmed Facts

- Current `PUT`, `DELETE`, and restore endpoints directly change inventory
  documents and their ledger effects when the caller has
  `inventory.documents.manage`.
- Existing non-legacy document writes reuse one inventory service and preserve
  the negative-balance guard. Legacy documents cannot be edited, deleted, or
  restored.
- `InventoryDocument` already has an audit-managed `updated_at` timestamp. It
  is not currently exposed by `InventoryDocumentPublic`.
- The managed scheduler and Celery delivery are at-least-once. A lease-expired
  scheduler run can be reclaimed, so a correction work item must not equate
  worker delivery with one business application.
- `AuditEvent` retains semantic events for 365 days. Structured operational
  logs are not a durable business-history reader.
- The only current business domain is inventory. A user may hold request,
  review, and recovery permissions at the same time; self-review is allowed.
- An approved correction must be applied by the scheduler as the System Actor.
  A terminal failure has no automatic retry. An authorized user may create a
  fresh automatic attempt with an empty recovery request.

## In Scope

1. Eligible targets are non-legacy inventory documents with ledger effects.
   Failed Excel imports remain validation failures and never create a
   correction request.
2. Correcting an eligible document supports `UPDATE_DOCUMENT`,
   `DELETE_DOCUMENT`, and `RESTORE_DOCUMENT`. Direct document update, delete,
   and restore must reject an eligible target with
   `{ "detail": "INVENTORY_CORRECTION_REQUIRED", "request_id": "..." }`
   and HTTP 409. Only the correction executor may use the existing write
   service for that target.
3. Add three correction permissions, each with the existing
   `inventory.documents.read` prerequisite:
   `inventory.corrections.request`, `inventory.corrections.review`, and
   `inventory.corrections.recover`. Do not create a separation-of-duties rule.
4. Creating a correction request immediately submits one immutable proposal.
   It includes the target ID, operation, expected `updated_at`, a required
   reason, and a server-generated proposal hash. `UPDATE_DOCUMENT` carries a
   complete `InventoryDocumentCreate` proposal; delete and restore carry no
   document proposal. The closed request and nested proposal DTOs reject
   unknown fields; the reason is trimmed, nonblank, and bounded; and
   `expected_updated_at` must be timezone-aware. The server validates,
   canonically serializes, and hashes only this typed, normalized proposal.
   There is no draft, assignment, in-place revision, file upload, or evidence
   form. A changed proposal is a new request and needs a new review.
5. The request lifecycle is `PENDING_REVIEW -> APPROVED`, `REJECTED`,
   `WITHDRAWN`, or `STALE`. After application, the request becomes `APPLIED`
   or `APPLICATION_FAILED`; recovery returns it to `APPROVED`. The work-item
   lifecycle is `APPROVED_PENDING_APPLY -> RUNNING -> SUCCEEDED` or
   `TERMINAL_FAILED`.
6. Approval creates exactly one independent application work item and its one
   `PENDING` initial attempt. Recovery appends one `PENDING` recovery attempt.
   The scheduler claims the pre-created attempt; it never inserts another one.
   The work item retains the fixed handler value
   `inventory.document_correction`; no generic registry, workflow runtime, or
   no-ledger sample handler is introduced in this task.
7. The executor locks the work item and target document, checks the expected
   `updated_at` in the same transaction, applies the existing inventory
   service, recalculates ledger effects, and commits the domain change,
   work-item outcome, and semantic audit event together.
8. A correction attempt is one business application opportunity, not one
   Celery delivery. A lost lease is recorded as `TERMINAL_FAILED` with a safe
   `EXECUTION_LOST` category and is never automatically applied again. A
   duplicate delivery of a completed or terminal attempt has no effect.
9. Recovery requires `inventory.corrections.recover`, an unchanged target
   timestamp and proposal hash, and an empty request body. It appends one new
   `PENDING` attempt and queues it for the same automatic executor. It never
   changes a proposal or exposes a manual apply endpoint. If another
   `PENDING_REVIEW` or `APPROVED` request exists for the same document, recovery
   returns a stable 409 without changing the failed request or appending an
   attempt. Concurrent request creation maps the active-request uniqueness
   conflict to the same stable 409.
10. Add one inventory-correction page with permission-filtered tabs for the
    caller's requests, the review queue, and the recovery queue. It is the
    owned UI for request entry, decision, status, and history; no separate
    workflow or audit-reader page is added. The existing document list provides
    a correction entry that opens this page with the document ID; no eligibility
    flag is added to the public document response.
11. Bootstrap one fixed, empty-config scheduler task every minute. It scans at
    most 20 pending attempts per run, disallows run-now and backfill, and treats
    an item-level terminal failure as a completed scan outcome rather than a
    failed scheduler run.

## Audit And Traceability

- `AuditEvent` records request creation, approval, rejection, withdrawal, and
  successful application. Each action has a code-owned, allowlisted summary;
  raw proposals, free-text reasons, files, credentials, and exception text are
  excluded.
- The immutable request, work item, and attempt records are the user-visible
  history. Terminal failure is persisted in the attempt row with a stable
  category. Existing Celery lifecycle logs remain operational telemetry; no
  correction business identifiers or custom log fields are emitted.
- Correction business rows are not automatically purged in this MVP.
  `AuditEvent`, scheduler-run, and operational-log retention retain their
  existing policies. Attempt records keep scheduler-run IDs as values, not
  foreign keys, so scheduler cleanup cannot remove business history.

## Acceptance Criteria

- [ ] An eligible document cannot be updated, deleted, or restored through the
  ordinary endpoint; create and import behavior remain unchanged.
- [ ] A permitted user creates an immutable submitted request without changing
  the document or ledger. The same user may review it when also granted review
  permission.
- [ ] Approval atomically creates one work item and no inventory effect.
  Duplicate approval and concurrent approval cannot create another work item.
- [ ] The executor applies a current proposal atomically with its ledger
  recalculation, work-item success, and audit event. A stale proposal or
  negative balance leaves inventory and ledger unchanged and becomes terminal.
- [ ] A lost lease and a repeated Celery delivery never create a second ledger
  effect or an automatic retry. Recovery appends one new attempt only when its
  permission and unchanged-target checks pass.
- [ ] Authorized UI/API users can request, review, withdraw, inspect, and
   recover corrections through one inventory page. Unauthorized users receive
   no action and no queue data.
- [ ] Unknown request/proposal fields, blank or oversized reasons, and
  timezone-naive `expected_updated_at` values are rejected before persistence;
  concurrent active-request creation and recovery conflicts return stable 409
  responses with `request_id` and `X-Request-ID`.
- [ ] Tests cover authorization, direct-write blocking, self-review, duplicate
  approval, timestamp staleness, negative balance, lease loss, duplicate
  delivery, terminal recovery, audit allowlists, and log redaction.

## Out Of Scope

- A generic approval engine, handler registry, workflow designer, assignment,
  notifications, reminders, escalation, timeout reminders, or automatic retry.
- Drafts, proposal revisions, attachments, evidence uploads, cancellation, a
  separate audit query UI, and a generic work-item UI.
- External side effects. The first handler is limited to the database
  transaction that owns the inventory and ledger update.

## D-007 Handoff

When completed, this task supplies the observed inventory request and
application boundary. D-007 may generalize only a demonstrated need, such as a
second handler type or an external side-effect contract. See
[deferred-iterations.md](./deferred-iterations.md) for the explicit handoff.
