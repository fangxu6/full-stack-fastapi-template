# Use Safe Celery Task Observability Context

Celery worker startup imports `app.core.celery` directly, so that module initializes the shared NDJSON observability sink rather than relying on FastAPI startup. Task execution uses the built-in `task_prerun` and `task_postrun` signals to clear context, validate and bind only the caller-provided canonical UUID `task_id` and registered application `task_name`, and emit `task.started`, `task.completed`, or `task.failed` at `INFO`. `task_postrun` is the unified cleanup boundary: it maps `SUCCESS` and `FAILURE` only when the accepted task context is already bound, while `RETRY`, `REJECTED`, `IGNORED`, unknown states, and identities rejected by prerun only clear context. Signal payloads may be accepted for Celery dispatch compatibility but are never read, forwarded, or serialized. No event contains task arguments, run IDs, users, recipients, configuration, or exception text. HTTP request context remains limited to `request_id` and `actor_kind`.

## Consequences

- The observability facade and its tests must permit these task-only fields while rejecting arbitrary context.
- Task logs correlate worker lifecycle without turning operational logs into a business-data store.
- Task-specific business state remains in PostgreSQL; logging cannot replace durable run or delivery records.
- The application does not introduce a custom Celery Task base class or per-task logging wrapper merely for this context; lifecycle signals cover all registered application tasks uniformly.
