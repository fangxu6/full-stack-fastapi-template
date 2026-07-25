# Use Celery And Redis For Background Runtime

Celery with Redis is the shared background-task runtime. Redis is limited to
the broker and short-lived technical task results; it is not a business data
store. Future alert delivery persists its business state in PostgreSQL before
enqueueing work.

## Consequences

- Workers use late acknowledgement, so business tasks must be idempotent.
- Task arguments are JSON-serializable identifiers or bounded values, never
  ORM instances or credentials.
- `runtime.ping` is the only task in the initial runtime; alerts, outbox rows,
  providers, retries, and named queues need separate approved work.
