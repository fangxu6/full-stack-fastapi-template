# Design: Separate Correction Review From Attempt Execution

## Boundary

The inventory correction domain keeps two concrete modules:

```text
correction_router.py
  -> correction_service.py       request/review/read/recovery
  -> existing documents.py       document + ledger mutation

scheduled_tasks.py
  -> correction_attempts.py      lease/claim/apply/terminal attempt policy
       -> documents.py            approved document correction only
```

`correction_service.py` remains the stable route-facing request/review entry
point. `correction_attempts.py` becomes the stable task-facing attempt
execution entry point. This is a concrete seam between two state families, not
a generic workflow abstraction.

## Ownership

### Request/review module

Retain these responsibilities in `correction_service.py`:

- request creation and immutable proposal validation/hash preparation;
- request list/detail projections and permission checks;
- approve, reject, withdraw, and recovery transitions;
- work-item/attempt public projections used by the API;
- request/review audit action contracts.

Recovery may append a pending attempt because it is the user-facing recovery
transition. It does not claim, lease, apply, or finalize that attempt.

### Attempt-execution module

Move these responsibilities to `correction_attempts.py`:

- expired lease detection and `EXECUTION_LOST` terminalization;
- pending attempt claim and work-item lease assignment;
- claimed attempt validation and approved document application;
- mapping document-domain failures to stable correction failure categories;
- success and terminal-failure state transitions for request/work-item/attempt;
- the `CorrectionApplicationError` used by the task's item-level error path.

The module keeps the existing row locks and state guards. It invokes
`documents.apply_approved_correction()` and does not reproduce document or
ledger mutation rules.

## Transaction And Side-Effect Contract

Both modules receive a caller-owned `Session` and only flush when the current
behavior requires it. They never call `commit()` or `rollback()`.

`InventoryCorrectionApplyTask` remains responsible for:

1. binding the system actor;
2. marking expired attempts and claiming a bounded batch;
3. committing the claim transaction before item execution;
4. opening a short application session per attempt;
5. rolling back a failed application and committing terminal failure in a
   separate transaction;
6. clearing the audit actor in `finally`.

HTTP routes retain `AuditedWriteSessionDep` and its existing request-scoped
commit/rollback behavior.

## Dependency Direction

The request/review module remains the owner of existing shared lookup,
projection, and correction-audit helpers used by both flows. The attempt module
may reuse those narrow helpers rather than copying them; it must not call a
route or task and must not expose a second API-facing facade. No third
repository/state-machine module is introduced.

## Compatibility

- No model, schema, migration, enum, route, Celery payload, or scheduler
  registry changes.
- Existing route imports continue to resolve through `correction_service`.
- `scheduled_tasks.py` changes only the module used for attempt functions and
  the exception type imported for item-level classification.
- Existing audit event names and exact safe `changes` keys remain unchanged.

## Test Surface

- Unit tests for attempt execution import `correction_attempts` directly for
  lease, claim, apply, and terminal state behavior.
- API correction tests continue to exercise request/review/recovery through
  the router and verify public state/history behavior.
- Scheduler task tests verify caller-owned commit/rollback boundaries,
  per-attempt failure isolation, and duplicate-delivery idempotency.

## Risks And Rollback

The main risk is accidentally moving a state transition or changing when the
task commits. Reduce it by moving functions without semantic rewrites, keeping
the old focused tests, and reviewing `git diff --check` plus the state-flow
tests before commit. Rollback is a single revert because the change is source
only and additive at the module level.
