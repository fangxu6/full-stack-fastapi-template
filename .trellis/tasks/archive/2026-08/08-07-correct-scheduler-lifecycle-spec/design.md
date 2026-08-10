# Design: Correct Scheduler Lifecycle Spec

## Objective

Update one active scenario in
`.trellis/spec/backend/async-task-guidelines.md` so its ownership language
matches the scheduler runtime and ADR-0012. The change is documentation only;
source is read-only evidence.

## Authoritative Runtime Model

| Owner | Responsibility | Boundary |
| --- | --- | --- |
| `tasks.py` | Re-export the legacy dispatch helper and register stable Celery names | Thin adapters over orchestration; no scanning or execution logic. |
| `orchestration.py` | Scan due jobs, lease and publish queued runs, coordinate worker phases, hand off alerts, clean up runs | Opens short explicit sessions and commits before broker, task, or alert work. |
| `execution.py` | Invoke a frozen task definition | Opens no session and returns `SchedulerRunOutcome`. |
| `run_lifecycle.py` | Create, claim, finalize, cancel, and delete `SchedulerRun` state | The only owner of durable lifecycle-field mutations; helpers flush but do not commit. |
| `scheduler_alerts.py` | Throttle job alerts and queue rendered emails | Owns `SchedulerJob` alert timestamps and outbox rows; never mutates `SchedulerRun`. |

The active scenario will describe this model at contract level, using the
existing names so it remains directly traceable without duplicating the whole
orchestration implementation.

## Corrected Worker Narrative

The example will replace the obsolete terminal call with this sequence:

1. `orchestration.execute_run()` calls `run_lifecycle.claim_execution(...)`
   in a short transaction and commits the claim.
2. `execution.execute(...)` receives frozen scalar/snapshot inputs and returns
   a `SchedulerRunOutcome` without database access.
3. `orchestration.execute_run()` calls
   `run_lifecycle.finish_outcome(..., outcome=outcome)` in a new short
   transaction, clears success alerts in that same durable phase when needed,
   and commits.
4. A failed outcome invokes `scheduler_alerts.send_alert(...)` only after that
   terminal transaction has completed.

This preserves the current at-least-once recovery model: a lease and durable
run state, not an in-memory task result, remain the idempotency boundary.

## Compatibility And Rollback

- No API, persistence, or process behavior changes.
- Existing ADR-0012 already states the same ownership model, so no ADR edit is
  required unless source evidence changes.
- Rollback is a path-scoped revert of the async-guide scenario. Do not revert
  the scheduler code or the earlier alert-ownership remediation.

## Validation Design

- Search the active specs for `finish_run` and the stale `tasks.py` ownership
  wording.
- Compare the final wording against ADR-0012 and the five current modules.
- Run the repository specification lint, task validation, and whitespace
  check. Runtime tests are not part of this documentation-only change.
