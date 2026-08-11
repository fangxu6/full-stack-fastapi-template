# Fence SchedulerRun Terminal Outcomes

## Goal

Prevent a stale or terminal scheduler Worker from overwriting the outcome owned
by a later execution claim, and prevent its result from changing scheduler
alerts.

## Confirmed Facts

- `claim_execution()` can reclaim an expired `RUNNING` run, replacing
  `lease_expires_at` and incrementing `attempt_count`
  (`backend/app/modules/scheduler/run_lifecycle.py:147-173`).
- `finish_outcome()` currently accepts only a run ID and writes terminal state
  without a row lock or execution-lease check (`run_lifecycle.py:176-194`).
- `orchestration.execute_run()` owns the claim, execute, terminal-write, and
  alert sequence (`backend/app/modules/scheduler/orchestration.py:168-225`).

## Requirements

### R1: Fence terminal persistence

- A terminal outcome is accepted only when the target run still exists, is
  `RUNNING`, and its persisted execution lease exactly matches the lease
  captured when that Worker claimed execution.
- The terminal write must lock the run row before evaluating those conditions.
- A stale, duplicate, cancelled, or already-terminal result is a no-op.

### R2: Preserve ownership of follow-up effects

- `execute_run()` must retain the lease returned by `claim_execution()` and
  supply it to terminal persistence.
- A rejected result must not clear success alerts or send a failure alert.
- An accepted current result retains the existing terminal state and alert
  behavior.

### R3: Keep the contract and coverage accurate

- Update the canonical scheduler transition matrix with the fenced terminal
  precondition and no-op concurrency behavior.
- Add focused PostgreSQL-backed regressions for terminal ownership and stale
  alert suppression.

## Out of Scope

- Exactly-once execution or generic deduplication of scheduled-task business
  side effects. Scheduler tasks remain at-least-once and own their own
  idempotency where required.
- Schema, Alembic, HTTP, frontend, and Celery message contract changes.
- The already-completed daily-report delivery lease repair.

## Acceptance Criteria

- [x] After Worker B reclaims and finishes a run, Worker A's late success and
  late failure cannot change the run's terminal fields.
- [x] A rejected late failure emits no alert, and a rejected late success does
  not clear existing failure alerts.
- [x] A current Worker can still persist `SUCCEEDED`, `SKIPPED`, or `FAILED`
  and preserve current alert behavior.
- [x] The scheduler matrix describes the implemented lease-fencing contract.
- [x] Focused scheduler tests and backend static quality checks pass against an
  isolated test database.
