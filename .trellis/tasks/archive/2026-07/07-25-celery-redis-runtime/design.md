# Celery And Redis Runtime Design

## Scope

Add a minimal asynchronous task runtime to the FastAPI deployment, plus one
bounded scheduled business task: daily inventory email reports. The runtime
still adds no public API, alert outbox, webhook channel, or user notification.
`runtime.ping` remains the diagnostic task for verifying the worker/broker
path.

## Architecture

```text
backend or diagnostic command
  -> Celery default queue (Redis database 0)
  -> celery-worker (one prefork process)
  -> runtime.ping result (Redis database 1, expires after 900 seconds)

celery-beat (Asia/Shanghai)
  -> 08:00 create prior-day inventory snapshots
  -> every 15 minutes queue due per-email deliveries
```

Redis is an internal broker and short-lived result backend, not a source of
business truth. Inventory report and delivery state is persisted in PostgreSQL;
tasks pass only those row identifiers through Celery.

## Runtime Boundaries

### Python Runtime

- Add `celery[redis]>=5.5,<6` to `backend/pyproject.toml`; the extra supplies
  the Redis transport/result-backend client, so no second direct Redis client
  dependency is added.
- Define the Celery application in `backend/app/core/celery.py`, beside the
  existing configuration and other platform-wide behavior.
- Define the one diagnostic task in `backend/app/core/tasks.py`; it accepts a
  JSON string up to 64 characters and returns it unchanged. It never touches
  a database, network service, credentials, or business model.
- Do not expose an HTTP route for dispatching or inspecting tasks.
- A future bounded module, such as `modules/alerting`, owns its task functions
  and explicit retry policy; it must not put business tasks into `core/tasks.py`.
- `modules/inventory/tasks.py` owns `inventory.daily_report.create`,
  `inventory.daily_report.retry`, and `inventory.daily_report.deliver`. Each
  task creates its own database session and receives only a report or delivery
  ID.

### Daily Inventory Report

- Beat runs creation at 08:00 `Asia/Shanghai`; creation accepts only the
  `[08:00, 08:15)` window and targets the preceding natural date. A missed
  window is intentionally skipped rather than backfilled.
- One `inventory_daily_report` row per processing unit and business date holds
  its name plus immutable raw-material and finished-product balance snapshots.
  Balances use the existing ledger aggregation with `business_date <= report
  date`; each category contains only nonzero rows, while an entirely empty
  report remains valid.
- The environment-only recipient mapping is validated at startup. On its first
  successful lookup, recipient email targets are persisted as
  `inventory_daily_report_delivery` rows. Missing mappings remain retryable so
  a later deployment configuration change can supply them.
- Each delivery row is claimed under a database lock, sent with the existing
  SMTP implementation, then marked successful or retryable. It permits eight
  total attempts at 15-minute intervals. A process failure after SMTP accepts
  mail may duplicate an email; the persisted state prevents silent loss and
  does not claim exactly-once delivery.

### Settings

Add typed settings to `app.core.config.Settings`:

| Setting | Default / requirement | Purpose |
| --- | --- | --- |
| `REDIS_HOST` | `redis` in Compose | Internal Redis service host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | required secret; reject `changethis` outside local | Redis authentication |
| `CELERY_VISIBILITY_TIMEOUT_SECONDS` | `3600`, positive | Redis broker recovery window |
| `CELERY_RESULT_EXPIRES_SECONDS` | `900`, positive | Short-lived result retention |

The broker and result URLs are derived properties, use different Redis logical
databases (`0` broker, `1` results), and percent-encode the password. Raw URLs
and the password must not be emitted to logs, tests, responses, or task
arguments.

### Celery Defaults

| Configuration | Value | Reason |
| --- | --- | --- |
| serializer / accepted content | JSON only | Serializable task boundary |
| default queue | Celery default queue | No unowned pre-created queues |
| worker concurrency | `1` | No measured workload justifies more processes |
| acknowledgement | late | Worker loss allows redelivery |
| worker-loss handling | reject/requeue | Preserve at-least-once behavior |
| prefetch multiplier | `1` | A single worker does not reserve extra work |
| automatic retry | none globally | Each business task explicitly owns retry policy |
| result expiration | `900` seconds | Diagnostic results are not durable facts |
| broker visibility timeout | `3600` seconds | Recovery boundary for interrupted work |

This is an at-least-once system. A task may run again after a worker loss;
future business tasks must be idempotent at their PostgreSQL/business boundary.
`runtime.ping` does not retry. Future alert tasks set `ignore_result=True` and
use outbox/delivery rows, not Celery results, for their status.

## Compose Topology

Production `compose.yml` adds three default-network services:

| Service | Command / role | Dependencies | Health behavior |
| --- | --- | --- | --- |
| `redis` | Redis with `requirepass`, AOF, named volume | none | authenticated `PING` |
| `celery-worker` | `celery -A app.core.celery:celery_app worker --concurrency=1` | Redis healthy, `prestart` complete | Celery remote-control ping to its fixed hostname |
| `celery-beat` | `celery -A app.core.celery:celery_app beat` | Redis healthy, `prestart` complete | Beat PID liveness |

Worker and Beat use the same backend image and environment wiring as the
backend, but neither has Traefik labels or a host port. They depend on Redis
and completed database migration/bootstrap; the HTTP backend does not depend
on Redis, so broker failure cannot prevent existing API startup or responses.

Redis uses a named volume and `appendonly yes`; no Compose port mapping is
added. The local override keeps `restart: "no"` and mirrors the production
service commands and configuration. Its CI path starts Redis, worker, and Beat
alongside the existing stack.

`REDIS_PASSWORD` is added to local environment configuration, deployment
documentation, and staging/production GitHub Environment secrets. It is passed
to Redis, worker, and Beat but never to a task payload or public API.

## Verification

Unit tests execute `runtime.ping` in Celery eager mode and verify input
validation plus the config constraints. A Docker Compose integration test starts
the actual worker and broker, dispatches `runtime.ping` from the backend
container, waits for its 900-second-backed result with a bounded client timeout,
and asserts the returned marker matches. This validates real serialization,
broker routing, worker consumption, and result retrieval without a new API.

No `e2e-api-tests.md` is created: this task changes no HTTP endpoint, request
schema, response schema, or browser flow.

## Failure And Rollback

- Redis unavailable: worker/Beat retry broker connection; existing HTTP API
  remains available because it does not dispatch a task in this task scope.
- Worker lost during a future task: late acknowledgement and the 3,600-second
  visibility window permit redelivery; idempotency remains the future task's
  responsibility.
- Redis restart: AOF and the named volume reduce queue-loss risk but do not
  turn Redis into a durable business system; PostgreSQL outbox is mandatory for
  future alert facts.
- Rollback: stop worker and Beat first, then remove task-dispatch callers in a
  future task if any. Do not remove Redis data while future outbox rows can
  still enqueue work. This task has no business rows or caller to unwind.

## Deferred Capabilities

See [deferred iterations](./deferred-iterations.md) for the scope register.

The approved alert design remains the follow-up reference. It owns
`alert_outbox`, `alert_delivery`, `alert_throttle`, provider adapters, routing,
and escalation policy. Named queues, higher concurrency, long-running tasks,
priorities, recovery reminders, and user-facing notifications require their
own task and load/operational review.
