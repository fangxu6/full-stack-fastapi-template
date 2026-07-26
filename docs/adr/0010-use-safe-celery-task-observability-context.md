# Use Safe Celery Task Observability Context

Celery task execution uses the built-in task lifecycle signals to clear context, bind only the broker-generated `task_id` and registered `task_name`, and emit `task.started`, `task.completed`, or `task.failed`. Every post-run path clears task context. No event contains task arguments, run IDs, users, recipients, configuration, or exception text. HTTP request context remains limited to `request_id` and `actor_kind`.

## Consequences

- The observability facade and its tests must permit these task-only fields while rejecting arbitrary context.
- Task logs correlate worker lifecycle without turning operational logs into a business-data store.
- Task-specific business state remains in PostgreSQL; logging cannot replace durable run or delivery records.
- The application does not introduce a custom Celery Task base class or per-task logging wrapper merely for this context; lifecycle signals cover all registered application tasks uniformly.
