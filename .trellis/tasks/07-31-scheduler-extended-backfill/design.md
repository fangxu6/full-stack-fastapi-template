# D-003 Technical Design: Extended Historical Backfill

## Design Summary

Keep the existing `POST /api/v1/scheduler/jobs/{job_id}/backfill` contract and
`SchedulerRunBackfill` payload. Extend the service-side historical check from
90 to 365 days, and gate the operation with the static backfill capability
defined by D-001. The request remains one timestamp and produces at most one
run. No migration, new permission, approval flow, queue, or dispatch API is
needed.

## Boundaries And Dependency

1. `scheduler.jobs.manage` remains the route-level RBAC boundary.
2. D-001 owns the capability metadata and its resolver/public projection. D-003
   calls that resolver for the persisted job's `class_path`; it must not add a
   second registry or infer capability from `SchedulerJob.config`.
3. The scheduler service owns validation and run creation. The route only parses
   the existing body and passes the actor and timestamp.
4. The existing dispatch scanner owns Celery leasing and the batch cap of 100.
   Backfill never calls Celery directly.
5. The existing page owns the modal. D-003 changes only the 365-day affordance,
   risk copy, and capability-dependent action state supplied by D-001.

D-001 must be implemented and reviewed before D-003 is activated. If D-001's
public field or helper name differs from this plan, update this document and the
implementation checklist before coding; do not create a parallel capability
contract.

## Request Flow

```text
POST /scheduler/jobs/{id}/backfill
  -> permission_required("scheduler.jobs.manage")
  -> service.backfill(actor_id, job_id, planned_at)
  -> get persisted job (read only)
  -> D-001 backfill capability check
  -> timezone / past / <=365-day validation
  -> matches_cron(..., Asia/Shanghai)
  -> create_run(MANUAL_BACKFILL, one row, frozen snapshot)
  -> commit through existing audited unit of work
  -> scheduler scanner claims the queued run and dispatches its numeric id
```

The capability check is deliberately before the existing timestamp checks. A
disallowed implementation class cannot use malformed timestamps to probe task
behavior, and every rejection path remains side-effect free. The service may
read the job and resolve its class, but it must not flush a run until every
check passes.

## Validation Contract

### Input and authorization

- `planned_at` must be timezone-aware, strictly earlier than `current`, and no
  older than 365 calendar days by the existing aware-datetime subtraction.
  Exactly 365 days is accepted when it also matches Cron.
- `matches_cron()` remains the sole Cron predicate and continues to normalize to
  `Asia/Shanghai` and minute precision.
- Route-level missing permission returns the existing permission error. A class
  whose D-001 capability is false returns the scheduler's existing validation
  error family (HTTP 422) with a safe, stable detail selected by D-001's
  contract.
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

- No database migration or public schema change is required by D-003 alone.
  Regenerate the frontend client only if D-001 adds capability fields to the
  public job schema.
- Existing 90-day requests, automatic scheduling, leases, active-run locking,
  and cleanup behavior remain compatible. A run created under the old limit is
  indistinguishable from a new valid manual backfill except for its timestamp.
- Rollback is configuration/code-only: restore the 90-day constant and modal
  bounds. Do not delete already-created runs; they continue through the normal
  lifecycle. A rollback must not alter audit rows or cancel unrelated runs.
- Deployment order is D-001, then D-003. Before enabling the UI, verify that
  every persisted scheduler class resolves the D-001 capability metadata; an
  unknown or invalid class must remain non-executable.

## Observability And Security

Keep the existing `MANUAL_BACKFILL`, requester UUID, audit actor propagation,
safe `error_category`/`error_summary`, and scheduler logs. Do not put credentials
or arbitrary class/config data in new request fields or Celery payloads. The
worker still receives only the numeric run ID and reloads the frozen snapshot.
