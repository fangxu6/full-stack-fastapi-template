# Concentrate scheduler run lifecycle state

## Goal

Make one scheduler-owned module the only place that persists `SchedulerRun`
lifecycle changes. This removes the shallow seam between durable run state and
task orchestration while preserving the intentional Celery Beat/Worker split.

## Background

- Beat scans enabled jobs and publishes a numeric run ID.
- A Worker claims the run ID and executes the frozen class/config snapshot.
- The current run writes are split between `service.py` (creation at
  `backend/app/modules/scheduler/service.py:312`, queued cancellation at
  `:420`, cleanup at `:500`) and `tasks.py` (dispatch lease at
  `backend/app/modules/scheduler/tasks.py:118`, execution and terminal state at
  `:258`).
- Scheduler alert throttling and `EmailOutbox` writes currently live in
  `tasks.py:35`; those writes need their own alert boundary because they update
  `SchedulerJob`, not `SchedulerRun`.

## Requirements

1. Add `backend/app/modules/scheduler/run_lifecycle.py` to own run creation,
   active-run checks, dispatch lease claim/retry, execution lease claim and
   reclaim, terminal writes, queued cancellation, and historical cleanup.
2. Add `backend/app/modules/scheduler/scheduler_alerts.py` to own scheduler
   alert throttling, `SchedulerJob` alert timestamps, and `EmailOutbox` writes.
3. Make `service.py` retain job CRUD, Cron handling, task-definition/config
   validation, and manual-operation validation while delegating every run
   persistence operation to `run_lifecycle.py`.
4. Make `tasks.py` retain Beat scanning, broker publishing, Worker task
   resolution/execution, and task orchestration while delegating every run
   persistence operation to `run_lifecycle.py` and every alert operation to
   `scheduler_alerts.py`.
5. Lifecycle and alert helpers receive a caller-owned `Session` for database
   work and do not publish Celery messages, send SMTP, or commit/rollback the
   caller's transaction. Background entrypoints keep transactions short and
   never span broker or email operations.
6. Preserve current statuses, lease timing, snapshot semantics, error
   categories, queue name, Celery task names, public schemas, database schema,
   and at-least-once behavior.

## Acceptance Criteria

- [ ] `SchedulerRun` status, lease, timestamp, retry, and deletion assignments
      occur only in `run_lifecycle.py`.
- [ ] `SchedulerJob` alert timestamp and outbox assignments occur only in
      `scheduler_alerts.py`.
- [ ] Beat still scans and dispatches, and Worker still claims and executes;
      neither phase is merged or moved into the other.
- [ ] Manual run creation, scheduled run creation, queued cancellation,
      dispatch retry, expired lease reclaim, terminal success/skip/failure, and
      cleanup retain their current observable behavior.
- [ ] Existing scheduler service/task/API tests pass, with focused lifecycle
      and alert tests covering the new ownership boundaries.
- [ ] No database migration, model/status change, public schema change,
      generated client change, queue change, or new generic state-machine
      abstraction is introduced.

## Out of Scope

- Combining Celery Beat and Worker execution.
- Adding queues, statuses, retry engines, public lifecycle APIs, or migrations.
- Rewriting business task implementations or email delivery.
