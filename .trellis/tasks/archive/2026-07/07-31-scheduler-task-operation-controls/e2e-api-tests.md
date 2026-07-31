# 定时任务人工操作能力 API 验收计划

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `http://127.0.0.1:8000/api/v1/utils/health-check/`
- Browser target: `http://localhost:5173`
- Isolation: use the scheduler API test database and a separately configured local Playwright test environment;
  create uniquely named jobs and do not use a development or production database. Mock the scheduler dispatcher
  when an API test needs to observe publish side effects.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Scheduler service capability helper | Synthetic `ScheduledTask` without overrides. | Resolve its capability through the service helper. | Both values are `true`. | No job/run writes or dispatch. | Explicit `false` overrides are separately verified. |
| E2E-002 | `POST /api/v1/scheduler/jobs/{id}/run-now` | Superuser and either deployed daily-report job. | Submit empty body. | `200`; `trigger=MANUAL_NOW`. | One queued run persists with class/config snapshot and requester; no direct publish. | A second active request retains existing `409` behavior. |
| E2E-003 | `POST /api/v1/scheduler/jobs/{id}/backfill` | Superuser and a deployed daily-report job; record current run IDs and mocked dispatch calls. | Submit a timezone-aware past time that matches its Cron. | `422`; detail names the unsupported manual backfill and body includes `request_id`. | No new `SchedulerRun`, audit write, job-state change, or Celery publish. | Same result for both create and retry daily-report classes. |
| E2E-004 | `POST /api/v1/scheduler/jobs/{id}/backfill` | Superuser and a default-capability task class with matching Cron. | Submit a timezone-aware past time within 90 days. | `200`; `trigger=MANUAL_BACKFILL`. | Exactly one queued run persists with UTC planned time, snapshot, and requester; existing scanner handles future dispatch. | Invalid time and active-run conflict retain existing validation/409 behavior. |
| E2E-005 | Scheduler management page | Superuser and a daily-report job. | Open `/scheduler/jobs`. | The row shows immediate-run but no backfill action. | No request is made merely by rendering buttons. | Users without `scheduler.jobs.manage` still see no mutable action buttons. |

## Execution

1. Start or verify the isolated backend with the health endpoint, then start the isolated frontend.
2. Run E2E-001 through E2E-004 through the backend test suite or direct isolated API fixture, with the dispatcher
   mocked as planned.
3. Run E2E-005 with the scheduler Playwright suite and assert both visibility states.
4. Record actual commands, environment identifiers, and concrete blockers in the task validation notes before
   task completion.
