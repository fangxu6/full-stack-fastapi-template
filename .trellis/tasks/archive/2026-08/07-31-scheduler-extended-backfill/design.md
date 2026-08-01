# D-003 Technical Design: Extended Historical Backfill

## Design Summary

Keep the existing `POST /api/v1/scheduler/jobs/{job_id}/backfill` contract and
`SchedulerRunBackfill` payload. Extend only the service-side historical check
from 90 to 365 days. The existing D-001 static capability already gates the
operation. The request remains one timestamp and produces at most one run. No
migration, new permission, approval flow, queue, dispatch API, or current
production task capability change is needed.

## Boundaries And Dependency

1. `scheduler.jobs.manage` remains the route-level RBAC boundary.
2. D-001 owns the capability metadata and its resolver/public projection. D-003
   calls that resolver for the persisted job's `class_path`; it must not add a
   second registry or infer capability from `SchedulerJob.config`.
3. The scheduler service owns validation and run creation. The route only parses
   the existing body and passes the actor and timestamp.
4. The existing dispatch scanner owns Celery leasing and the batch cap of 100.
   Backfill never calls Celery directly.
5. The existing page owns the modal. D-003 changes only its 365-day affordance
   and concise risk copy; existing `can_backfill` behavior continues to hide
   the action for disallowed classes.

The current D-001 contract is `task_capabilities(class_path=...)` in the
scheduler service and `can_backfill` on public job responses. Both existing
inventory classes explicitly return false. `ScheduledTask.allow_backfill`
defaults to false, so D-003 deliberately preserves that outcome: a future class
opts in only when its implementer explicitly declares `True` and can give
historical `planned_at` a replay-safe business meaning.

## Request Flow

```text
POST /scheduler/jobs/{id}/backfill
  -> permission_required("scheduler.jobs.manage")
  -> service.backfill(actor_id, job_id, planned_at)
  -> timezone / past / <=365-day validation
  -> get persisted job (read only)
  -> matches_cron(..., Asia/Shanghai)
  -> existing D-001 backfill capability check
  -> create_run(MANUAL_BACKFILL, one row, frozen snapshot)
  -> commit through existing audited unit of work
  -> scheduler scanner claims the queued run and dispatches its numeric id
```

The current service validates the submitted timestamp and Cron before resolving
the persisted class capability. D-003 preserves that simple, established order:
there is no separate ordering guarantee beyond rejecting every invalid input
before `create_run()`. The service may read the job and resolve its class, but
it must not flush a run until every check passes.

## Validation Contract

### Input and authorization

- `planned_at` must be timezone-aware, strictly earlier than `current`, and no
  older than `timedelta(days=365)` by the existing aware-datetime subtraction.
  Exactly 365 days is accepted when it also matches Cron.
- `matches_cron()` remains the sole Cron predicate and continues to normalize to
  `Asia/Shanghai` and minute precision.
- Route-level missing permission returns the existing permission error. A class
  whose D-001 capability is false returns the scheduler's existing validation
  error family (HTTP 422) with its stable D-001 detail. This remains true for
  both current inventory tasks; D-003 does not add an exception.
- Time, Cron, capability, and active-run errors must leave no new `SchedulerRun`,
  audit mutation, or broker call.

### Run and persistence

On success, call the existing `create_run()` exactly once with:

- `trigger=SchedulerRunTrigger.MANUAL_BACKFILL`;
- `planned_at` converted to UTC by the existing model path;
- `requested_by=actor_id`;
- default `QUEUED` status and `next_dispatch_at=current`.

`create_run()` continues to lock the job row, enforce one active run, freeze the
locked job's `class_path` and JSON config, and preserve the nested savepoint
around unique conflicts. The API response remains `SchedulerRunPublic`; no
range or batch fields are added.

## Frontend Design

The existing Shanghai `datetime-local` modal remains the only entry point:

- derive `min` from current Shanghai local time minus 365 days, rounded up to
  the next local minute because the input has minute precision, and keep `max`
  at current Shanghai local time;
- retain the `toShanghaiIso()` conversion and let the server revalidate the
  timezone, age, and Cron match;
- show concise copy for Shanghai time, the 365-day maximum, exact Cron match,
  one-run-per-submit behavior, and possible task side effects;
- use the D-001 capability projection to hide or disable the backfill action for
  disallowed implementation classes;
- surface the server's safe validation message instead of claiming a 90-day
  limit; do not add date-range, batch, or multi-select controls.

## Compatibility, Operations, And Rollback

- No database migration or public schema change is required by D-003. D-001
  has already added the capability fields, so this task does not regenerate the
  frontend client.
- Existing 90-day requests, automatic scheduling, leases, active-run locking,
  and cleanup behavior remain compatible. A run created under the old limit is
  indistinguishable from a new valid manual backfill except for its timestamp.
- Rollback is configuration/code-only: restore the 90-day constant and modal
  bounds. Do not delete already-created runs; they continue through the normal
  lifecycle. A rollback must not alter audit rows or cancel unrelated runs.
- Before enabling the 365-day window, verify that current inventory classes
  still resolve to `can_backfill=false`; an unknown or invalid class also
  remains non-executable. Future classes become eligible only through their
  static declaration, never through job data.

## Observability And Security

Keep the existing `MANUAL_BACKFILL`, requester UUID, audit actor propagation,
safe `error_category`/`error_summary`, and scheduler logs. Do not put credentials
or arbitrary class/config data in new request fields or Celery payloads. The
worker still receives only the numeric run ID and reloads the frozen snapshot.
