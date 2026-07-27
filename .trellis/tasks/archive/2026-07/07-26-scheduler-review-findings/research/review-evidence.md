# Scheduler Review Evidence

## Reviewed baseline

- Review target: `c8175af44f83da24d27e54f41fa4df7111a867da`.
- Partial post-review baseline: `0d3c59d` adds `NoDecode` and a dotenv CSV
  regression test. Keep it; this task must not duplicate or revert that change.
- Historical scheduler configuration is out of scope: the user confirmed that
  neither `scheduler_job.config` nor `scheduler_run.config` contains
  credentials.

## Confirmed findings

1. `backend/app/modules/scheduler/config.py:20-22` declared
   `list[EmailStr]` without `NoDecode`; pydantic-settings tried JSON decoding
   before the CSV `BeforeValidator`.
2. `backend/app/core/celery.py:51-58` used `worker_init` and `beat_init`.
   Celery `Signal.send()` catches receiver exceptions, so missing production
   alert configuration did not stop either process.
3. `backend/app/modules/scheduler/service.py:29-31,99-107` omitted sensitive
   key variants and only inspected direct `SecretStr` annotations.
4. `backend/app/modules/scheduler/tasks.py:171-179` selected and re-sent every
   `QUEUED` run on each scan without a dispatch lease, cap, or retry schedule.
5. `backend/app/modules/scheduler/tasks.py:218-248` handled class/config
   validation and `task.run()` in one `ValueError` boundary, misclassifying
   business failures as configuration failures.
6. `backend/app/modules/scheduler/service.py:265-290` had a check-then-insert
   active-run race and called `session.rollback()` after a non-committing flush,
   which can discard earlier updates in the scanner batch.
7. `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:482` used a UTC
   ISO value for `datetime-local.max` while submitted input is explicitly
   interpreted as `+08:00`.

## Design constraints established by evidence

- Keep PostgreSQL as the durable scheduler source of truth and Redis only as
  the Celery broker/result backend.
- Keep one default queue, at-least-once execution, current visibility timeout,
  and business-task idempotency. Do not add a queue, APScheduler, generic
  retries, or automatic history cleanup for credentials.
- `next_dispatch_at` is internal persistence state; do not expose it through
  public schemas or regenerate the frontend OpenAPI client solely for it.
