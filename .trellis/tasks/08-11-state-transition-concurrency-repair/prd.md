# Harden state transition concurrency and repair session records

## Goal

Make the documented daily-report and scheduler transition guarantees true in
the existing runtime, and restore one-record-per-session Trellis history after
the `36d492b` merge conflict.

## Background

- `docs/state-machine-unified-transition-design.md` is the canonical state
  transition record and states that it reflects current code behavior.
- Daily-report delivery claims create a lease, but completion and failure paths
  accept a delivery ID without proving the caller still owns that lease. A late
  worker can therefore overwrite a newer result.
- Scheduler cancellation is documented as row-locked, but
  `cancel_queued_runs()` reads queued runs without `FOR UPDATE` and can race
  with execution claim.
- The merge combined two unrelated session records and duplicated session 52
  in the workspace index and journal.

## Requirements

### R1: Daily-report stale-result protection

- Preserve the delivery lease value in the task payload created at claim time.
- Accept a completion or failure result only when the delivery remains
  `DELIVERING` and its persisted lease equals the payload lease.
- A stale or duplicate result must not mutate the delivery or refresh the
  parent report.
- Update the daily-report transition matrix to describe the implemented guard.

### R2: Scheduler cancel/claim serialization

- Lock rows selected by `cancel_queued_runs()` so cancellation cannot act on a
  stale queued snapshot after another transaction claims execution.
- Keep the scope limited to the cancel/claim race; do not fold the separately
  deferred `finish_outcome()` ownership redesign into this task.
- Keep the scheduler matrix accurate after the code change.

### R3: Trellis session-history repair

- Split the malformed combined journal entry into one record per historical
  session and use chronological, continuous numbers:
  - 51: `35a805a` scheduler lifecycle specification
  - 52: `31f2003` frontend and guide specification refresh
  - 53: `ce6443a` unified state transition contract
  - 54: `febcd91` frontend baseline runtime defects
- Make the index and journal agree on totals, numbering, titles, commits, and
  branch metadata.

## Acceptance Criteria

- [ ] A late daily-report delivery success or failure result after a subsequent
  claim is a no-op and cannot overwrite that claim's terminal state or parent
  report rollup.
- [ ] An in-lease daily-report result still completes or schedules retry as it
  did before.
- [ ] A cancellation and execution claim on the same scheduler run serialize
  through row locking; a run claimed first is not later written as cancelled by
  a stale cancellation read.
- [ ] Focused PostgreSQL-backed regression tests cover both concurrency
  boundaries.
- [ ] The state-transition document matches the implemented behavior.
- [ ] Trellis journal and index have unique, continuous session numbers through
  session 54 and one complete record per session.

## Out of Scope

- Schema changes, new state-machine abstractions, and a generic workflow
  runtime.
- Scheduler result ownership or stale-result changes outside the cancel/claim
  race. See [deferred iterations](./deferred-iterations.md).
- Rewriting unrelated historical journals or task archives.

## Open Questions

None. The user accepted the reviewed scope and repository evidence determines
the implementation boundaries.
