# Correct Scheduler Lifecycle Spec

## Goal

Correct the active scheduler lifecycle guidance so engineers follow the current
five-part ownership boundary instead of the removed `finish_run(...)` API and
the former `tasks.py` orchestration model. This prevents a future scheduler
change from reintroducing split `SchedulerRun` writes or the prior alert/outbox
ownership violation.

## Confirmed Facts

- **F-002 (P1):** `.trellis/spec/backend/async-task-guidelines.md:208-225`
  says `tasks.py` may scan, publish, resolve, and execute, then shows the
  removed `run_lifecycle.finish_run(...)` terminal call.
- `backend/app/modules/scheduler/tasks.py:4-15` re-exports the existing
  dispatch helper for compatibility and registers the three stable Celery task
  names as thin adapters over `orchestration.py`; it owns no scanning or
  execution orchestration.
- `backend/app/modules/scheduler/orchestration.py:42-232` owns due-run
  scanning, dispatch leasing and broker handoff, worker-phase coordination,
  terminal alert handoff, and historical cleanup.
- `backend/app/modules/scheduler/execution.py:20-69` executes the frozen run
  inputs without opening a database session and returns `SchedulerRunOutcome`.
- `backend/app/modules/scheduler/run_lifecycle.py:50-228` owns durable
  `SchedulerRun` creation, dispatch/execution claims, terminal persistence via
  `finish_outcome(...)`, queued cancellation, and retention cleanup.
- `backend/app/modules/scheduler/scheduler_alerts.py:17-92` owns
  `SchedulerJob` alert timestamps and `EmailOutbox` writes. This is consistent
  with ADR-0012 after the `configuration_alerted_at` ownership remediation.

## Requirements

### R1. Correct the stale active scenario

Replace the inaccurate ownership wording and obsolete `finish_run(...)` example
in the Scheduler Run Lifecycle Ownership scenario. No active specification may
state or imply that `tasks.py` owns scheduler scanning or execution
orchestration.

### R2. Record the current ownership contract

The corrected scenario must identify these responsibilities:

1. `tasks.py`: a compatibility export plus Celery task-name registration; no
   scanning or execution orchestration.
2. `orchestration.py`: scan, dispatch, Beat/Worker handoff, short transaction
   phases, and scheduler-level coordination.
3. `execution.py`: pure frozen-input execution and `SchedulerRunOutcome`
   construction.
4. `run_lifecycle.py`: every durable `SchedulerRun` lifecycle-field change,
   including terminal `finish_outcome(...)` persistence.
5. `scheduler_alerts.py`: `SchedulerJob` alert throttles and rendered outbox
   rows; it never changes `SchedulerRun` state.

### R3. Preserve established reliability boundaries

Keep the at-least-once, active-run uniqueness, dispatch/execution lease,
caller-owned transaction, and durable-outbox rules unchanged. The worker
example must show `execution.execute(...)` producing an outcome before
`run_lifecycle.finish_outcome(...)` persists it, with broker, business-task,
and alert work outside the completed durable phase.

### R4. Keep scope documentation-only

This task changes the one stale scheduler scenario and its own planning
artifacts. It does not change scheduler source, tests, public API contracts,
schema, migrations, dependencies, generated clients, or runtime configuration.

## Acceptance Criteria

- [ ] The active scheduler lifecycle scenario contains no `finish_run(...)`
      reference and does not assign scanning or execution orchestration to
      `tasks.py`.
- [ ] The scenario documents all five current owners from R2 and distinguishes
      pure execution outcome construction from durable lifecycle persistence.
- [ ] `run_lifecycle.finish_outcome(..., outcome=SchedulerRunOutcome)` is the
      sole documented terminal persistence transition, and
      `scheduler_alerts.py` remains the owner of alert timestamps/outbox rows.
- [ ] The corrected wording preserves the existing lease, idempotency,
      caller-owned transaction, and post-commit alert invariants without
      proposing runtime behavior changes.
- [ ] `python .trellis/scripts/spec_wiki.py lint`, path-scoped stale-term
      searches, `python .trellis/scripts/task.py validate
      .trellis/tasks/08-07-correct-scheduler-lifecycle-spec`, and
      `git diff --check` pass.

## Out Of Scope

- Changes under `backend/app/modules/scheduler/**` or any other product source,
  tests, generated clients, database schema, dependencies, migrations, or
  runtime configuration.
- Reorganizing the full async guide for length or guide governance. That work
  belongs to `08-07-refresh-frontend-and-guide-spec-contracts` and must retain
  this corrected ownership contract.
- API E2E testing. This task changes no request, response, persistence, or
  runtime behavior.

## Open Questions

None. Repository evidence and the parent task's documentation-only boundary
resolve the scope and acceptance decisions.
