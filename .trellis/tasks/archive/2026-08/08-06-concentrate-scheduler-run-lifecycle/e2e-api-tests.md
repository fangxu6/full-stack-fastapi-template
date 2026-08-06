# Scheduler Lifecycle API Validation

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: the backend test database selected by the repository test
  configuration; no development database writes are permitted.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `POST /api/v1/scheduler/jobs/{job_id}/run-now` | Authenticated user with scheduler manage permission; enabled or disabled valid job | Empty JSON body | Existing `SchedulerRunPublic`, status `QUEUED`, trigger `MANUAL_NOW` | One frozen run row with `next_dispatch_at` set; no direct broker call from HTTP | A second active run returns the existing conflict response and creates no second active row |
| E2E-002 | `POST /api/v1/scheduler/jobs/{job_id}/disable` | Job with one queued run | Empty JSON body | Existing `SchedulerJobPublic`, disabled | Queued run becomes `CANCELLED`, has `finished_at`, and has no lease/dispatch timestamp | A running run is not cancelled by this operation |
| E2E-003 | `GET /api/v1/scheduler/jobs/{job_id}/runs` after Worker completion | Job with a run completed by `scheduler.execute_run` | Authenticated read request | Existing `SchedulerRunsPublic` with terminal run | Terminal status, category, completion timestamp, and cleared lease fields are persisted | A duplicate execution delivery does not create another run or change a terminal run into a second active run |

## Execution

Run the focused backend tests first. Execute these API cases only when an
isolated backend and database are available; record any concrete environment
blocker in `implement.md` rather than substituting a development database.
