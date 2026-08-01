# D-003 API E2E Test Plan

## Environment

- Target backend: `http://127.0.0.1:9000`
- Health check: `GET http://127.0.0.1:9000/api/v1/utils/health-check/`
- Isolation: run against the repository-required `aiadmin_test` PostgreSQL
  database; do not write fixtures to the development DB.
- Auth fixtures: reuse the repository's `superuser_token_headers` for the
  allowed path and a managed user/token fixture with `scheduler.jobs.manage`
  removed for the RBAC denial path. Use a test-only `ScheduledTask` class pair
  from D-001: one capability-allowed and one capability-denied class.
- Persistence checks use the same SQLModel session after each request. Capture
  the run count and IDs before the request so rejected cases can prove no
  insertion.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `POST /api/v1/scheduler/jobs/{job_id}/backfill` | Enabled job using a test-only or future replay-safe D-001 allowed class, Cron `0 8 * * *`, no active run; actor has `scheduler.jobs.manage` | `{"planned_at":"<now_minus_365_days_plus_one_minute_in_shanghai>+08:00"}` where the time is an exact Cron occurrence | `200`; body has `trigger=MANUAL_BACKFILL`, `status=QUEUED`, UTC `planned_at`, and actor `requested_by` | Exactly one new run; class path/config equal the job snapshot; `next_dispatch_at` is set; no direct Celery call | Assert the exact 365-day boundary separately with a deterministic service clock; this API case avoids current-second/minute precision drift |
| E2E-002 | Same backfill endpoint | Same allowed job, no active run | `planned_at` older than 365 days by one minute | `422` scheduler validation error | Run count, audit state, and queued-message spy unchanged | No `SchedulerRun` is created |
| E2E-003 | Same backfill endpoint | Same allowed job; token lacks `scheduler.jobs.manage` | Valid 365-day Cron-matching payload | `403` permission denial | No run, audit mutation, or broker call | Capability is not evaluated as a way around RBAC |
| E2E-004 | Same backfill endpoint | Job uses D-001 denied class; actor has `scheduler.jobs.manage` | Valid 365-day Cron-matching payload | `422` capability/validation denial | No run, audit mutation, or broker call | Global manage permission cannot override class capability |
| E2E-005 | Same backfill endpoint | Allowed job with no active run | Four subrequests: future, current, timezone-naive, and Shanghai time not matching Cron | Each returns `422` | No subrequest adds a run or changes existing rows | Error paths are side-effect free and do not call Celery |
| E2E-006 | Same backfill endpoint | Allowed job with one existing `QUEUED` or `RUNNING` run, plus an unrelated job with no active run | Valid 365-day Cron-matching payload | `409` active-run conflict | Existing run and unrelated job remain unchanged; no second run | Nested savepoint does not roll back the unrelated job's state |
| E2E-007 | One request dispatch boundary | Allowed job, no active run; monkeypatch/spy shared dispatcher | Submit one valid payload, then invoke the existing due-run scanner | HTTP creates one run; scanner uses the normal lease and numeric run ID | One run is claimed/enqueued; no per-request direct `.delay`, no duplicate queued rows | Existing 100-row scanner cap and lease fields remain effective |
| E2E-008 | Snapshot and audit flow | Allowed job with a non-empty JSON config and actor; no active run | Submit a valid historical payload, then edit the job before the run executes | `200` on submit; later run execution uses original snapshot | `requested_by`, class path, config, and `MANUAL_BACKFILL` remain original; later job edit is separate | No credentials or mutable client data are introduced into the run or Celery payload |
| E2E-009 | Existing inventory task regression | Either current inventory class; actor has `scheduler.jobs.manage` | Valid past Cron-matching payload | `422` with the existing unsupported-backfill detail | No run, audit mutation, or broker call; job remains `can_backfill=false` | D-003 must not make an existing task replayable merely by widening the age bound |

## Frontend Contract Checks

These are browser checks attached to the same isolated API data, not substitutes
for the API cases above:

- The backfill input's Shanghai-local `min` is current time minus 365 days,
  rounded up to the next minute, and `max` is current Shanghai local time.
- The modal shows the 365-day, exact-Cron, one-run, and side-effect warning; the
  stale 90-day message is absent.
- D-001 denied jobs have no executable backfill action; allowed jobs still have
  exactly one submit path and no range/batch controls.
- The two current inventory task rows still expose no backfill action. A
  test-only allowed job proves the shared modal can use the 365-day range
  without turning either production task into a replayable job.

## Execution

1. Start the isolated backend and verify the health endpoint.
2. Apply test fixtures and run E2E-001 through E2E-009 against the local API.
3. Run the frontend browser checks against `http://localhost:5173` when the
   scheduler page is available.
4. Record command output, failed case IDs, and any concrete environment blocker
   in `implement.md` or the Trellis journal.
