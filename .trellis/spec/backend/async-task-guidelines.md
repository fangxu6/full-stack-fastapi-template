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

## Scenario: Daily Inventory Email Reports

### 1. Scope / Trigger

- Beat creates previous-day reports at 08:00 `Asia/Shanghai`, and scans due
  email deliveries every 15 minutes.
- It sends operational reports through existing SMTP only. It adds no API,
  front-end view, alert provider, or named queue.

### 2. Signatures

- Tasks: `inventory.daily_report.create`, `inventory.daily_report.retry`, and
  `inventory.daily_report.deliver(delivery_id: int)`.
- Tables: `inventory_daily_report` and `inventory_daily_report_delivery`.
- Setting: `INVENTORY_DAILY_REPORT_RECIPIENTS`, a JSON mapping of processing
  unit UUID to an email list.

### 3. Contracts

- Creation accepts only `[08:00, 08:15)` Shanghai time and records the prior
  natural day. A missed window is skipped; it is never backfilled.
- Create one immutable report snapshot for every enabled processing unit,
  including empty inventories. Snapshot raw materials and finished products
  separately, keep nonzero balances only, and aggregate ledger rows through
  `business_date <= report_date`.
- Validate UUID keys and email values at startup. After the first successful
  resolution, persist one delivery target per email. A missing mapping remains
  retryable and is re-read by later scans.
- Tasks pass only report/delivery IDs, open their own sessions, and lock/claim
  rows before SMTP. Each email permits eight total attempts; success must not
  resend. SMTP acceptance followed by worker loss may duplicate mail, so the
  implementation guarantees at-least-once, not exactly-once, delivery.
- These are automated operational records with UTC technical timestamps, not
  user actions; do not fabricate an audit actor.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Creation outside the 08:00--08:15 window | Skip without creating or backfilling a report. |
| No recipient mapping | Persist retryable report failure and retry configuration lookup after 15 minutes. |
| SMTP delivery fails | Record a safe error category, schedule only that email for retry. |
| Delivery reaches attempt eight | Mark it terminal; do not queue another attempt. |
| Worker dies after SMTP accepts mail | A redelivery can duplicate mail; database state must remain recoverable. |

### 5. Good / Base / Bad Cases

- Good: a task receives `delivery_id`, claims it, sends one rendered snapshot,
  then persists the result independently from other recipients.
- Base: an active unit with no stock still receives an empty report email.
- Bad: recomputing a report after later ledger correction, sending every
  recipient in one task, or passing recipient configuration through Celery.

### 6. Tests Required

- Cover configuration parsing, Beat registration/timezone, cutoff aggregation,
  empty snapshot, immutability, window skip, and unique report creation.
- Cover individual SMTP success/failure, missing recipients becoming available,
  retry scans, eight-attempt termination, and no resend after success.

### 7. Wrong Vs Correct

#### Wrong

```python
send_daily_report.delay(processing_unit_id, report_date, recipients)
```

This loses durable per-email progress and can recompute a changed balance.

#### Correct

```python
deliver_inventory_daily_report.delay(delivery_id)
```

The task reloads and locks a frozen delivery record, then updates its durable
attempt state after SMTP returns.
