# Separate correction review from attempt execution

## Goal

Deepen the inventory correction workflow by separating request/review state
transitions from attempt execution state transitions. The result should make
each state family local and make the route/task callers' transaction ownership
explicit, without changing the public API, database schema, or document
mutation module.

## Background And Confirmed Facts

- `backend/app/modules/inventory/correction_service.py` currently owns request
  creation, review, recovery, read projections, attempt lease/claim, document
  application, and terminal failure transitions.
- HTTP routes call only request/review/recovery functions. The scheduled task
  calls `mark_expired_attempts_terminal`, `claim_pending_attempts`,
  `apply_claimed_attempt`, and `finalize_failed_attempt`.
- `backend/app/modules/inventory/documents.py` already owns document and ledger
  mutation. Correction execution must continue to call that existing module.
- HTTP mutation routes use `AuditedWriteSessionDep`; scheduled tasks open and
  commit their own short-lived sessions. Correction service functions currently
  do not commit or roll back.
- The correction request, work item, attempt models, enums, API schemas, route
  paths, scheduler payload, and audit event contract are already deployed
  contracts for this refactor.

## Requirements

1. Keep request creation, review decisions, read projections, access checks,
   and recovery in the request/review module.
2. Move attempt lease expiry, pending-attempt claim, claimed-attempt document
   application, failure finalization, and attempt terminal state helpers into a
   dedicated attempt-execution module.
3. Keep document mutation in the existing inventory document module. The new
   attempt-execution module may invoke its existing approved-correction entry
   point but must not duplicate document or ledger rules.
4. Keep transaction ownership with callers: routes/tasks decide when to
   commit, rollback, bind the audit actor, and clear it. Neither deepened
   module may commit or roll back.
5. Preserve all existing function behavior, state values, error categories,
   idempotency checks, leases, audit summaries, and safe exception handling.
6. Update scheduled-task imports and focused tests so the module seam is
   exercised directly. Do not add a generic workflow/state-machine framework,
   new persistence, API fields, queue messages, or client changes.

## Out Of Scope

- Renaming or redesigning the correction API.
- Changing correction request/work-item/attempt tables, migrations, enum
  values, indexes, or retention rules.
- Moving document/ledger writes out of `modules/inventory/documents.py`.
- Adding a repository layer, handler registry, protocol, generic state machine,
  retry engine, notification, or external side effect.
- Changing the scheduler run lifecycle or Celery message format.

## Acceptance Criteria

- [ ] Request/review/recovery callers no longer import or execute attempt
      lease/application/terminal functions from the request/review module.
- [ ] The attempt-execution module contains the complete lease, claim, apply,
      failure, and terminal state policy and is directly unit-testable.
- [ ] The document module remains the only owner of document/ledger mutation.
- [ ] No new module commits or rolls back; HTTP and scheduled-task callers
      retain the current transaction boundaries and audit actor lifecycle.
- [ ] Existing API responses, database writes, state transitions, audit event
      payloads, lease behavior, duplicate delivery behavior, and failure
      categories remain unchanged.
- [ ] Correction route tests and scheduler/task tests pass, including success,
      negative-balance failure, stale target, lease loss, recovery, and
      duplicate delivery cases.
- [ ] Backend lint and type checks pass; the final diff contains no migration,
      generated client, or unrelated files.

## Resolved Decisions

- Keep `correction_service.py` as the request/review-facing entry point to
  minimize caller churn; add a focused `correction_attempts.py` module for the
  execution state family.
- Keep small shared lookup/audit helpers where they already serve both flows;
  do not introduce a third generic persistence or state module solely to make
  the split look symmetrical.
- Preserve existing public function names for request/review callers and use
  the new module explicitly from `scheduled_tasks.py`.

## Open Questions

None. The requested boundary, compatibility constraints, and acceptance
behavior are explicit.

## Notes

This is a refactor-only task. It must not alter the correction business
contract established by the archived inventory exception-correction task.
