# Use Safe Celery Task Observability Context

## Status

Accepted for task-context validation and cleanup. The task-exception
prohibition is superseded by [ADR-0013](./0013-restrict-detailed-celery-task-failure-logging.md).

## Context

Celery worker startup imports `app.core.celery` directly, so that module must
initialize the shared NDJSON observability sink rather than relying on FastAPI
startup. Lifecycle signals provide a uniform context boundary for all
registered application tasks.

## Decision

The built-in `task_prerun` signal clears context, validates and binds only the
caller-provided canonical UUID `task_id` and registered application `task_name`,
then emits `task.started` at `INFO`. `task_postrun` emits `task.completed` only
for `SUCCESS` when accepted task context is already bound, and clears context
in `finally` for every exit path. `FAILURE`, `RETRY`, `REJECTED`, `IGNORED`,
unknown states, and identities rejected by prerun emit no postrun terminal event.
The `task_failure` signal emits the single `task.failed` event at `ERROR` under
[ADR-0013](./0013-restrict-detailed-celery-task-failure-logging.md). Signal
payloads may be accepted for Celery dispatch compatibility but are never read,
forwarded, or serialized.

HTTP request context remains limited to `request_id` and `actor_kind`.

## Consequences

- The observability facade and its tests permit the validated task-only fields
  while rejecting arbitrary context.
- Task logs correlate worker lifecycle without turning operational logs into a
  business-data store.
- Task-specific business state remains in PostgreSQL; logging cannot replace
  durable run or delivery records.
- The application does not introduce a custom Celery Task base class or
  per-task logging wrapper merely for this context; lifecycle signals cover all
  registered application tasks uniformly.

## Related Decisions

- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)
- [ADR-0013: Restrict Detailed Celery Task-Failure Logging](./0013-restrict-detailed-celery-task-failure-logging.md) (supersedes only the exception-detail prohibition)
