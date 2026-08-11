# State Transition Concurrency Repair Implementation Plan

## 1. Daily-report Delivery Fence

- Extend `DeliveryPayload` with `lease_expires_at`.
- Populate it after `_delivery_payload()` writes the delivery lease.
- Add one locked current-lease predicate shared by completion and failure.
- Pass the payload, rather than only its ID, into both result handlers.
- Add stale-success and stale-failure regression coverage in
  `backend/tests/modules/inventory/test_daily_report.py`.

## 2. Scheduler Cancel/Claim Lock

- Add `with_for_update()` to `cancel_queued_runs()`.
- Add a focused two-session PostgreSQL regression under
  `backend/tests/modules/scheduler/` that pauses immediately after the
  cancellation SELECT and proves claim cannot win the race.

## 3. Contract and Records

- Correct the two affected matrix rows in
  `docs/state-machine-unified-transition-design.md`.
- Split the malformed journal record and renumber subsequent entries in
  `.trellis/workspace/fx/journal-1.md` and `index.md`.

## 4. Validation

- Run focused daily-report and scheduler test modules against an existing
  isolated PostgreSQL test database.
- Run backend lint and type checks for modified Python files.
- Run `git diff --check` and the relevant Trellis task/spec validation.
- Confirm the working tree contains only this task's files and implementation
  changes in addition to the user's pre-existing changes.

## Rollback Points

- Revert the daily-report and scheduler commits independently if their focused
  regressions expose compatibility issues.
- Revert the journal-only commit independently; it has no runtime effect.

## Deferred Scope

The scheduler result-ownership hardening excluded from this implementation is
tracked in [deferred iterations](./deferred-iterations.md).
