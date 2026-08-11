# State Transition Concurrency Repair Design

## Boundaries

This task corrects two domain-local concurrency boundaries and their canonical
documentation. It does not introduce a shared state-machine runtime, a new
database column, or an API contract.

## Daily Report Delivery

`InventoryDailyReportDelivery.lease_expires_at` already identifies a specific
claim. Extend the in-process `DeliveryPayload` with that value after
`_delivery_payload()` changes the row to `DELIVERING`.

Both `_complete_delivery()` and `_fail_delivery()` will receive the payload,
lock the row, and proceed only when all of these are true:

1. the row still exists;
2. its status is `DELIVERING`; and
3. its persisted `lease_expires_at` exactly matches the payload value.

Otherwise they return without changing the delivery or refreshing its parent
report. The Celery task still carries only the delivery ID; the claimed payload
is retained inside the one worker invocation, matching the current dispatch
shape. This is the smallest fencing token available in the existing schema.

The focused regression creates payload A, expires and reclaims the delivery as
payload B, completes B, and then applies A's late success and failure results.
The delivery and report must remain delivered.

## Scheduler Cancellation

`cancel_queued_runs()` will add `with_for_update()` to its queued-run query.
Under PostgreSQL READ COMMITTED, this serializes cancellation with
`claim_execution()`: whoever locks first commits its transition, while the
second query re-evaluates the row predicate and acts only if it is still
queued.

The regression uses two sessions and an SQLAlchemy query-execution barrier
immediately after cancellation's SELECT. Before the barrier is released, a
claim must remain blocked. Once cancellation commits, claim returns `None` and
the run remains `CANCELLED`. The test fails against the existing unlocked
SELECT because claim can commit `RUNNING` while cancellation holds only a
stale ORM snapshot.

`finish_outcome()` remains unchanged. Its broader stale-result ownership issue
is already documented as a deferred scheduler-specific design task and is not
required to close the cancel/claim race. See [deferred iterations](./deferred-iterations.md).

## Documentation and History

The state transition matrix will describe daily delivery result acceptance as
an exact lease comparison and scheduler cancellation as a row-locked query.

The workspace records will become four independent entries ordered by commit
time: sessions 51 through 54. The index total becomes 54 and its table mirrors
the journal exactly. No archived task identifiers are renamed.

## Compatibility and Rollback

- No migration, endpoint, client, or task-message format changes are required.
- The daily-report change turns stale result writes into no-ops, which is the
  documented idempotency contract.
- Reverting the runtime commit restores the prior race behavior; documentation
  and journal repairs should remain unless their corresponding code is also
  reverted.
