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

## Scenario: Scheduler Dispatch And Configuration Boundary

### 1. Scope / Trigger

- Trigger: code creates, dispatches, or executes a `SchedulerRun`, or changes
  scheduler alert/runtime configuration.
- PostgreSQL remains the scheduler source of truth; Celery/Redis only carries
  a run ID for at-least-once execution.

### 2. Signatures

- Celery app import: `app.core.celery:celery_app`.
- Tasks: `scheduler.scan_due_jobs()` and `scheduler.execute_run(run_id: int)`.
- Internal run field: `scheduler_run.next_dispatch_at TIMESTAMPTZ NULL` with
  partial index `ix_scheduler_run_queued_dispatch` for `status = 'QUEUED'`.
- Alert configuration: `SCHEDULED_TASK_ALERT_RECIPIENTS` is CSV email input;
  `SchedulerSettings` uses `NoDecode` so environment and `.env` sources share
  the CSV parser.

### 3. Contracts

- Outside `local`, importing the Celery app validates SMTP plus alert
  recipients before creating the app. Worker and Beat therefore exit nonzero
  on missing configuration; FastAPI startup must not import this module.
- Scheduler task configuration rejects credential-like keys and any Pydantic
  JSON Schema node with `format: password`, including nested models,
  containers, unions, and `$defs`. Validate before saving job config, frozen
  run snapshots, or exposing task schema.
- New `QUEUED` runs set `next_dispatch_at` to their creation time. Dispatch
  claims only due queued rows with `FOR UPDATE SKIP LOCKED`, orders by
  `created_at, id`, caps a batch at 100, and advances the lease by
  `CELERY_VISIBILITY_TIMEOUT_SECONDS` before broker send.
- Broker-send failure returns a queued run to the next minute; a worker clears
  `next_dispatch_at` when it moves the run to `RUNNING`. The field is internal
  persistence state and is never added to public scheduler schemas.
- All active-run creation paths lock the `SchedulerJob` row before checking
  the active-run constraint. Scanner inserts use a savepoint so one unique
  conflict cannot roll back other jobs in the same scan.
- Frozen class/config failures are `CONFIGURATION_INVALID`; after successful
  construction, every uncontrolled `run()` exception, including `ValueError`,
  is `EXECUTION_FAILED`. `ScheduledTaskSkipped` remains a controlled skip.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| `staging` or `production` Celery import lacks SMTP or recipients | Worker/Beat process exits nonzero before consuming messages. |
| HTTP app starts without scheduler email settings | Startup remains available; runtime validation is not imported. |
| Submitted config has `credential`, `authorization`, `access_key`, password-schema field, or equivalent | Return the unified 422 error before any job/run JSONB write. |
| Queued run has an active dispatch lease | Do not send it again until the lease expires. |
| One broker send fails in a claimed batch | Keep other sends independent and retry that run on the next scan minute. |
| Concurrent active-run insert conflicts | Return/record the overlap without rolling back other scanner updates. |
| Task business code raises `ValueError` | Persist `FAILED/EXECUTION_FAILED` and use the failure alert limit. |

### 5. Good / Base / Bad Cases

- Good: a manual run commits a `QUEUED` record, then the shared dispatch helper
  claims only that run and sends its numeric ID.
- Base: a broker accepts a message just before a process dies; the queued row
  is eligible again after the visibility timeout and business idempotency
  handles a possible duplicate.
- Bad: a scan selects every queued run each minute, passes config or ORM
  objects through Celery, catches task `ValueError` as configuration failure,
  or adds secrets to scheduler JSONB.

### 6. Tests Required

- Cover real environment and dotenv CSV sources, duplicate/invalid recipient
  rejection, and Worker/Beat CLI failure with FastAPI import isolation.
- Cover nested/container/union secret schema and credential-key rejection at
  service and API boundaries, including no persisted job on 422.
- Cover dispatch lease, broker-send retry timing, 100-row cap, active-run
  conflict savepoint isolation, and migration upgrade/downgrade.
- Cover configuration-invalid versus business-`ValueError` terminal status,
  alert category, and retained `ScheduledTaskSkipped` behavior.

### 7. Wrong Vs Correct

#### Wrong

```python
queued_ids = session.exec(
    select(SchedulerRun.id).where(SchedulerRun.status == "QUEUED")
).all()
for run_id in queued_ids:
    celery_app.tasks["scheduler.execute_run"].delay(run_id)
```

This creates an unbounded duplicate-message storm while a worker is busy or
Redis is unavailable.

#### Correct

```python
run.next_dispatch_at = now + LEASE_DURATION
session.commit()
celery_app.tasks["scheduler.execute_run"].delay(run.id)
```

Claim and persist the dispatch lease before broker send, then let the durable
record become eligible again only after the defined retry boundary.

## Scenario: Scheduler Audit Actor Propagation

### 1. Scope / Trigger

- Trigger: scheduler code scans, bootstraps, executes, finalizes, or throttles
  an alert for an audited `SchedulerJob`.
- This scenario complements the database audit-actor contract. It does not add
  audit fields to `SchedulerRun`, daily reports, or deliveries.

### 2. Signatures

```python
ScheduledTaskContext(
    run_id: int,
    actor_id: uuid.UUID,
    trigger: SchedulerRunTrigger,
    planned_at: datetime,
    started_at: datetime,
)
execute_run(run_id: int) -> None
```

- Celery receives only `run_id`. `actor_id` exists only in the in-process task
  context after the run is reloaded from PostgreSQL.

### 3. Contracts

- A scheduled scan, bootstrap, and alert-throttling path resolves and binds the
  default private System Actor key `system` in its local session before mutating
  `SchedulerJob`.
- Manual `MANUAL_NOW` and `MANUAL_BACKFILL` rows persist the initiating human
  in `requested_by`. `execute_run()` uses that durable UUID for task-owned and
  final `SchedulerJob` mutations, including retry/reclaim execution.
- A scheduled `SchedulerRun` keeps `requested_by=NULL`; the default System
  Actor is audit context, not public or business run attribution.
- Clear the bound actor when a local session's scoped audit work ends. Keep the
  existing commit/rollback and dispatch-leasing owners unchanged.

### 4. Validation and Error Matrix

| Condition | Required behavior |
| --- | --- |
| Manual run has a persisted requester | Bind that UUID for audited worker mutations. |
| Scheduled run has no requester | Resolve default System Actor key `system` and bind it locally. |
| Default System Actor absent during scheduler mutation | Fail before an audited flush; do not fabricate a UUID. |
| Broker retry/reclaim | Reload `requested_by`; retain the original human actor. |
| Daily report/delivery task | Retain technical timestamp-only behavior; do not bind an actor. |

### 5. Good / Base / Bad Cases

- Good: `execute_run(run_id)` reloads its row, derives the actor, then builds a
  `ScheduledTaskContext` without placing actor data on Celery.
- Base: a scheduled run has no human requester but a successful finalization
  correctly audits its job as the default System Actor.
- Bad: `execute_run(run_id, actor_id)` makes a retry depend on broker payload
  and permits attribution tampering.

### 6. Tests Required

- Assert manual run, retry, and reclaim retain the original `requested_by` for
  final audited job mutations.
- Assert scheduled scanning, bootstrap, and alert-throttling mutations use the
  default System Actor key `system` while `SchedulerRun.requested_by` remains
  `NULL`.
- Assert daily-report and delivery tests retain no actor binding.

### 7. Wrong vs Correct

#### Wrong

```python
execute_run.delay(run.id, current_user.id)
```

#### Correct

```python
execute_run.delay(run.id)
# Worker reloads run.requested_by or resolves the System Actor locally.
```

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
