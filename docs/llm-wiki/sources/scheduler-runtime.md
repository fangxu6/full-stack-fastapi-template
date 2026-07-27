---
title: Scheduler Runtime Source
created: 2026-07-27
updated: 2026-07-27
type: source
tags:
  - llm-wiki
  - backend
  - scheduler
  - celery
  - postgres
status: active
source_count: 3
---

# Scheduler Runtime Source

## Sources

- Path: `.trellis/spec/backend/async-task-guidelines.md`
  Role: Executable scheduler dispatch, configuration, and verification contract.
- Path: `.trellis/tasks/07-26-scheduler-review-findings/`
  Role: Reviewed implementation decision, migration plan, E2E cases, and evidence.
- Paths: `backend/app/modules/scheduler/`, `backend/app/core/celery.py`, and
  `backend/app/alembic/versions/d7e2a5c9f8b1_add_scheduler_run_dispatch_lease.py`
  Role: Current implementation of the durable scheduler runtime boundary.

## Key Facts

- PostgreSQL is the source of truth for scheduler definitions and runs; Celery
  carries only a numeric run ID and preserves at-least-once execution.
- Outside `local`, importing `app.core.celery:celery_app` validates scheduler
  SMTP and alert-recipient settings. FastAPI startup must not import that
  runtime boundary.
- Scheduler config rejects credential-like JSON keys and Pydantic JSON Schema
  nodes with `format: password`, including nested models, containers, unions,
  and `$defs`, before a job or frozen run snapshot is persisted or exposed.
- `scheduler_run.next_dispatch_at` is internal state. A dispatcher claims due
  `QUEUED` runs with `FOR UPDATE SKIP LOCKED`, orders by `created_at, id`, caps
  each batch at 100, and persists a visibility-timeout lease before broker
  send. Broker-send failure makes the run eligible on the next scan minute.
- Active-run creation locks the corresponding `SchedulerJob` row before the
  active-run check. Scanner inserts use savepoints so a unique conflict cannot
  roll back other jobs in the same scan batch.
- Frozen class/config failures are `CONFIGURATION_INVALID`; after construction,
  all uncontrolled task execution failures, including `ValueError`, are
  `EXECUTION_FAILED`. `ScheduledTaskSkipped` remains a controlled terminal
  state.
- Scheduler configuration history was confirmed not to contain credentials.
  Historical JSONB scanning, cleanup, deletion, and credential rotation remain
  outside this capability's scope.

## Durable Guidance

- Never scan and enqueue every queued run each minute. Use the persisted
  dispatch lease and batch cap so worker backlog or broker outage cannot form a
  duplicate-message storm.
- Keep `next_dispatch_at` out of public scheduler API schemas and generated
  frontend types; it is dispatch bookkeeping, not a user-facing run state.
- Treat `datetime-local` inputs as Shanghai UTC+8 wall-clock values and submit
  them as UTC; do not render a UTC ISO string directly as the local maximum.
- Verify this boundary with isolated PostgreSQL, a mock broker/SMTP path,
  migration upgrade and downgrade, and a browser backfill flow.

## Related Pages

- [[docs/llm-wiki/sources/backend-architecture|Backend architecture source]]
- [[docs/llm-wiki/entities/fastapi-backend|FastAPI backend]]
- [[docs/llm-wiki/entities/react-frontend|React frontend]]
