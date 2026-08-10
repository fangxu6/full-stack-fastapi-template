# Scheduler Lifecycle Source Snapshot

Captured during planning on 2026-08-10. Product source is read-only evidence
for this documentation-only child task.

## Active Specification Defect

`.trellis/spec/backend/async-task-guidelines.md:208-225` currently says that
`tasks.py` may scan, publish, resolve, and execute. Its worker example calls
the removed `run_lifecycle.finish_run(...)` API. No current source symbol has
that name.

## Current Runtime Ownership

| Module | Verified responsibility |
| --- | --- |
| `backend/app/modules/scheduler/tasks.py:4-15` | Compatibility re-export of `dispatch_queued_runs` plus registration of three stable Celery task names. It delegates to orchestration. |
| `backend/app/modules/scheduler/orchestration.py:42-232` | Due-job scan, dispatch claim/publish/retry, Worker coordination, post-commit alert handoff, and cleanup. |
| `backend/app/modules/scheduler/execution.py:20-69` | Frozen-input task execution with no database session; returns `SchedulerRunOutcome`. |
| `backend/app/modules/scheduler/run_lifecycle.py:50-228` | All durable `SchedulerRun` state creation, claims, terminal outcome persistence, cancellation, and retention cleanup. |
| `backend/app/modules/scheduler/scheduler_alerts.py:17-92` | `SchedulerJob` alert timestamps and rendered `EmailOutbox` rows; no `SchedulerRun` mutation. |

## Terminal Worker Flow

`orchestration.execute_run()` claims the run through
`run_lifecycle.claim_execution(...)` and commits. It then calls
`execution.execute(...)` with frozen values. In a new transaction it calls
`run_lifecycle.finish_outcome(..., outcome=outcome)`, clears success alerts in
that durable phase when applicable, commits, and only then hands a failure to
`scheduler_alerts.send_alert(...)`.

## Decision And Editing Boundary

ADR-0012 already describes the same five-part topology. Correct only the
Scheduler Run Lifecycle Ownership scenario in
`.trellis/spec/backend/async-task-guidelines.md`; do not change runtime code,
tests, ADR-0012, public contracts, or persistence behavior.
