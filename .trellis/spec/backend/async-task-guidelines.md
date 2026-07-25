# Async Task Runtime Guidelines

## Scenario: Celery And Redis Background Tasks

### 1. Scope / Trigger

- Trigger: code dispatches background work through the shared Celery runtime.
- Redis is the authenticated broker and short-lived result backend. PostgreSQL
  remains the durable source of business facts.

### 2. Signatures

- Celery app: `app.core.celery:celery_app`
- Diagnostic task: `runtime.ping(value: str) -> str`, with at most 64
  characters.
- Worker command: `celery -A app.core.celery:celery_app worker --concurrency=1`
- Runtime settings: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`,
  `CELERY_VISIBILITY_TIMEOUT_SECONDS`, and `CELERY_RESULT_EXPIRES_SECONDS`.

### 3. Contracts

- Tasks receive only JSON-serializable values. Pass identifiers, then create a
  database session and reload records inside a future task.
- `REDIS_PASSWORD` is required and cannot be `changethis` outside `local`.
- The broker uses Redis database `0`; short-lived results use database `1` and
  expire after `CELERY_RESULT_EXPIRES_SECONDS` (900 seconds by default).
- `task_acks_late=True`, `task_reject_on_worker_lost=True`, and visibility
  timeout (3,600 seconds by default) provide at-least-once execution. Future
  business tasks must be idempotent at their PostgreSQL boundary.
- Do not add global automatic retries, routes, or named queues. A future task
  explicitly declares its retry behavior and uses the default queue unless
  justified by a separate operational design.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Missing `REDIS_PASSWORD` | Settings construction fails at startup. |
| Default Redis password outside local | Settings construction fails. |
| Non-positive Celery timeout | Settings validation fails. |
| `runtime.ping` input is not a string or exceeds 64 characters | Raise `ValueError`; do not enqueue business work. |
| Worker dies after receiving a future business task | Broker may redeliver; task persistence must tolerate repeat execution. |

### 5. Good / Base / Bad Cases

- Good: an outbox task receives a delivery ID, opens its own session, and
  records a provider attempt idempotently.
- Base: a technical diagnostic returns a short value and uses Redis result
  expiration.
- Bad: a task receives an ORM object, stores alert state in Redis, or assumes
  its side effect executes exactly once.

### 6. Tests Required

- Unit tests cover settings validation, Redis URL escaping, and bounded task
  input.
- Use Celery eager mode for the task unit path.
- Integration validation dispatches `runtime.ping` and asserts a live worker
  returns the same marker through Redis.

### 7. Wrong Vs Correct

#### Wrong

```python
send_alert.delay(alert_model)
```

The ORM instance is process-local and task retry can duplicate an untracked
side effect.

#### Correct

```python
deliver_alert.delay(alert_outbox_id)
```

The task reloads the durable outbox row and records its idempotent delivery
transition in PostgreSQL.
