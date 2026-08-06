# Design: Concentrate Scheduler Run Lifecycle State

## Boundaries

`run_lifecycle.py` is the persistence boundary for `SchedulerRun`. It exposes
small operations for the existing callers:

- create a frozen queued or terminal run snapshot;
- inspect/lock an active job run;
- claim due queued runs for dispatch and release a failed broker claim;
- claim a queued run or an expired running run for execution;
- record a terminal result and clear dispatch/execution lease fields;
- cancel queued runs for a disabled job; and
- delete finished runs older than the existing retention period.

The module does not import Celery, task implementations, SMTP, or the alert
configuration.

`service.py` keeps its current public service functions. Its `create_run`,
`set_enabled`, delete guard, and cleanup compatibility paths call lifecycle
helpers instead of assigning `SchedulerRun` fields directly.

`tasks.py` keeps the external orchestration. It opens a session for each
durable phase, invokes lifecycle helpers, commits, then closes the session
before calling the broker or executing the task. It does not assign run fields.

`scheduler_alerts.py` owns the existing alert throttle and outbox behavior. It
may update `SchedulerJob` alert timestamps and create outbox rows, but it does
not update `SchedulerRun`.

## Data Flow

1. HTTP/manual or Beat scan calls the service/lifecycle create operation.
   The helper locks the job, checks the active-run invariant, snapshots class
   path/config, and sets `next_dispatch_at` for queued runs.
2. Beat calls the lifecycle dispatch claim operation in a short transaction.
   The helper locks due queued rows with `SKIP LOCKED`, advances the dispatch
   lease, and returns IDs. Beat commits before publishing each ID.
3. A broker failure calls the lifecycle release operation in a new short
   transaction, making the run eligible at the next scan minute.
4. The Worker calls the lifecycle execution claim operation. It either gets a
   queued/expired run and commits `RUNNING` plus a lease, or exits without
   executing. Task resolution and business execution happen after that commit.
5. The Worker calls the lifecycle terminal operation in a new short
   transaction. It records success, controlled skip, or failure, sets
   `finished_at`, and clears both lease fields. Failure alerts go through the
   alert module after the transaction.
6. Cleanup calls the lifecycle deletion operation from its own short
   transaction.

## Compatibility

- Keep `service.create_run` and `service.cleanup_runs` as thin delegating
  functions because existing tests and internal callers use those names.
- Keep Celery task names and signatures unchanged.
- Keep `SchedulerRun` and `SchedulerJob` models, status/trigger enums, JSON
  snapshots, exception types, and public API schemas unchanged.
- Preserve audit actor binding in the caller that owns the operation: HTTP
  dependencies bind the request actor, Beat binds the system actor, Worker
  binds the requesting/system actor, and alert code binds its passed actor.

## Trade-offs and Risks

- The lifecycle module is intentionally a focused collection of persistence
  functions, not a generic state machine; the existing enum and database
  constraints remain the source of allowed states.
- Returning a claimed `SchedulerRun` lets the Worker copy the existing frozen
  execution fields before its claim transaction closes; no new transport DTO
  is needed.
- Direct field-assignment searches and focused tests provide the guard against
  future lifecycle leakage. No runtime registration or migration is needed.

## Rollback

The change is source-only and preserves existing function/task contracts. If
focused tests expose a regression, restore the service/task delegation at the
same call sites while retaining the ADR and task artifacts; no database
rollback is required.
