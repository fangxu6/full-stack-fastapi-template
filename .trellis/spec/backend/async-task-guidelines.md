# Async Task Runtime Guidelines

## Scenario: Celery And Redis Background Tasks

### 1. Scope / Trigger

- Trigger: code dispatches background work through the shared Celery runtime.
- Redis is the broker and short-lived result backend. Local development uses
  unauthenticated Redis; production requires Redis authentication. PostgreSQL
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
- `REDIS_PASSWORD` is optional in `local`: an empty value produces Redis URLs
  with no authentication component. It is required in `production` and cannot
  be `changethis` outside `local`.
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
| Empty `REDIS_PASSWORD` in `local` | Build unauthenticated Redis URLs and do not issue `AUTH`. |
| Missing `REDIS_PASSWORD` in `production` | Settings construction fails at startup. |
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

- Unit tests cover local no-password Redis URLs, production password
  validation, Redis URL escaping, and bounded task input.
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

#### Wrong

```python
return f"redis://:{quote(self.REDIS_PASSWORD, safe='')}@{host}:{port}/0"
```

This sends Redis `AUTH` even when a local Redis instance has no password.

#### Correct

```python
credentials = f":{quote(password, safe='')}@" if password else ""
return f"redis://{credentials}{host}:{port}/0"
```

Local Redis connects without authentication, while a production settings
validation error prevents an empty password from reaching this branch.

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

- Celery import does not require SMTP or scheduler alert recipients. Durable
  email producers must create an outbox row even when SMTP is absent; delivery
  records `SMTP_NOT_CONFIGURED` and retries later. An empty scheduler recipient
  list produces no outbox rows, but still advances the alert throttle and logs
  `scheduler.alert.unsent`.
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
| Celery import lacks SMTP or scheduler recipients | Worker/Beat remains available; the outbox delivery records a retryable SMTP failure, and scheduler alert throttling still completes. |
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
  rejection, and Worker/Beat import without SMTP or recipients.
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

### Scheduler Run Lifecycle Ownership

`backend/app/modules/scheduler/run_lifecycle.py` is the only module allowed to
assign `SchedulerRun` status, lease, dispatch, execution, terminal, retry, and
retention fields. `service.py` may validate jobs and delegate run creation,
queued cancellation, active-run reads, and cleanup. `tasks.py` is a thin
Celery adapter: it preserves the dispatch-helper export and registers stable
task names, but does not scan jobs or coordinate execution. `orchestration.py`
owns due-job scanning, dispatch leasing and broker handoff, Beat/Worker phase
coordination, post-commit alert handoff, and historical cleanup.
`execution.py` executes frozen task inputs without a database session and
returns a `SchedulerRunOutcome`. `scheduler_alerts.py` owns `SchedulerJob`
alert timestamps and `EmailOutbox` writes; it must not update `SchedulerRun`.

Lifecycle helpers accept a caller-owned `Session`, flush when a caller needs
database-generated values, and never commit or rollback. HTTP, Beat, Worker,
and cleanup callers commit their own short durable phase before broker,
business-task, or email work. The Worker flow is therefore:

```python
run = run_lifecycle.claim_execution(session=session, run_id=run_id, now=now)
session.commit()
outcome = execution.execute(...)  # frozen inputs captured from the claimed run
run_lifecycle.finish_outcome(session=session, run_id=run_id, outcome=outcome)
if outcome.status is SchedulerRunStatus.SUCCEEDED:
    scheduler_alerts.clear_success_alerts(session=session, job_id=job_id)
session.commit()
if outcome.status is SchedulerRunStatus.FAILED:
    scheduler_alerts.send_alert(...)  # opens its own post-commit session
```

The terminal lifecycle update and any success-alert reset share the second
short durable phase; failure alert handoff occurs only after it commits. Do not
merge Beat dispatch and Worker execution into one function or add a generic
state-machine abstraction. The database enum, partial active-run index,
dispatch lease, and execution lease remain the lifecycle invariants.

## Scenario: Scheduler Manual Operation Capabilities

### 1. Scope / Trigger

- Trigger: a `ScheduledTask` implementation needs to disable an unsupported
  human `MANUAL_NOW` action, or to explicitly opt in to a replay-safe human
  `MANUAL_BACKFILL` action without adding a database configuration or a new
  permission.

### 2. Signatures

```python
class ScheduledTask:
    allow_run_now: ClassVar[bool] = True
    allow_backfill: ClassVar[bool] = False

task_capabilities(*, class_path: str) -> tuple[bool, bool]
backfill(
    *,
    session: Session,
    actor_id: uuid.UUID,
    job_id: int,
    planned_at: datetime,
    now: datetime | None = None,
) -> SchedulerRun
```

- Read-only job response fields: `can_run_now: bool` and `can_backfill: bool`.
- Enforced endpoints: `POST /scheduler/jobs/{job_id}/run-now` and
  `POST /scheduler/jobs/{job_id}/backfill`.

### 3. Contracts

- `allow_run_now` defaults to `True`; `allow_backfill` defaults to `False`.
  A future task class may set `allow_backfill = True` only when its
  implementation gives `ScheduledTaskContext.planned_at` a replay-safe
  historical business meaning and preserves its own idempotency.
- Both values are Python implementation metadata, never job/run JSON, database
  state, or client input.
- `run_now()` and `backfill()` read the class path from the job before calling
  `create_run()`. The router exposes the same derived values through every
  `SchedulerJobPublic` response, and the frontend uses them only to hide
  unavailable buttons.
- A permitted backfill additionally requires a timezone-aware, strictly past,
  Cron-matching timestamp no older than `timedelta(days=365)`, inclusive at the
  exact age boundary. It creates one `QUEUED` `MANUAL_BACKFILL` run and relies
  on the existing shared dispatcher; it never publishes Celery work directly.
- Inventory daily-report creation and retry both set `allow_backfill = False`:
  neither replays `ScheduledTaskContext.planned_at`, so a historical run would
  not have the requested business meaning.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| `allow_run_now` is `True` | Preserve existing immediate-run creation, snapshot, requester, active-run conflict, and dispatch-lease behavior. |
| `allow_backfill` is explicitly `True` and the timestamp is valid | Preserve one existing `MANUAL_BACKFILL` run creation, snapshot, requester, active-run conflict, and dispatch-lease behavior. |
| Matching static value is `False` | Raise `SchedulerValidationError` with 422 `detail + request_id` before `create_run()`; do not persist a run or publish Celery work. |
| Backfill timestamp is current/future, timezone-naive, older than 365 days, or does not match Cron | Raise `SchedulerValidationError` with 422 `detail + request_id` before the capability check can create a run. |
| A saved job class path no longer resolves | Return `can_run_now=false` and `can_backfill=false` in job responses so the definition remains manageable; manual operations raise `SchedulerValidationError` 422 before `create_run()`. |
| Browser receives `can_* = false` | Do not render that operation's existing button; this is only a usability hint, not authorization. |
| Capability values are absent from config JSON | Do not read them; the implementation class inherits `allow_run_now=True` and `allow_backfill=False`. |

### 5. Good / Base / Bad Cases

- Good: a future replay-safe class explicitly sets `allow_backfill = True`; an
  exact 365-day Cron-matching timestamp creates one queued run through the
  shared dispatch path.
- Base: a task class that does not override either value supports immediate
  execution but reports `can_backfill=false`.
- Bad: enabling backfill through `config["allow_backfill"]`, declaring it for a
  task that ignores historical `planned_at`, trusting the hidden button as
  enforcement, or creating a queued run before deciding the operation is
  unsupported.

### 6. Tests Required

- Unit-test the inherited `allow_backfill=False` default and an explicit
  replay-safe `True` override through the service helper.
- Seed a previously valid job with an unresolvable class path; list/detail must
  remain `200` with both capabilities false, while manual run/backfill returns
  unified 422 and creates no run.
- Test exact 365-day acceptance and older/current/future/naive/Cron-invalid
  rejection at the service/API boundary, each with no `SchedulerRun`, audit
  mutation, or direct dispatch on failure.
- Assert API job payloads carry both `can_*` fields and use a browser test to
  verify the unavailable action is absent and the allowed modal uses the
  Shanghai-local 365-day minute-safe bounds. Regenerate the generated client
  only when its public schemas change.

### 7. Wrong Vs Correct

#### Wrong

```python
class InventoryReportTask(ScheduledTask):
    allow_backfill = True

    def run(self, *, context, config):
        create_report_for_today()

if job.config.get("allow_backfill"):
    create_run(...)
```

The class promises a historical replay it cannot honor, while database JSON can
also change a safety-relevant capability and discover a rejection too late.

#### Correct

```python
class ReplaySafeTask(ScheduledTask):
    allow_backfill = True

    def run(self, *, context, config):
        replay_business_state(planned_at=context.planned_at)

_, can_backfill = task_capabilities(class_path=job.class_path)
if not can_backfill:
    raise SchedulerValidationError("scheduled task does not support backfill")
return create_run(...)
```

The explicit static contract and service check both occur before any persistent
run or broker side effect exists.

## Scenario: Scheduler Cron Next-Run Preview

### 1. Scope / Trigger

- Trigger: the scheduler management UI needs to explain a submitted Cron
  expression before the definition is saved, without changing scheduler state.
- This is Cron interpretation only. It is not a `SchedulerJob` lookup,
  `SchedulerRun` creation path, task-class capability check, or Celery action.

### 2. Signatures

```python
preview_cron(*, cron_expression: str, now: datetime | None = None) -> tuple[
    datetime, list[datetime]
]
```

- Endpoint: `GET /scheduler/cron-preview?cron_expression=<expression>`.
- Permission: `scheduler.jobs.read`.
- Public response: `SchedulerCronPreviewPublic` with `base_at: datetime`,
  `timezone: Literal["Asia/Shanghai"]`, and `next_run_ats: list[datetime]`
  constrained by `Field(min_length=5, max_length=5)`.

### 3. Contracts

- Accept only the submitted `cron_expression`; do not accept a job ID, task
  class, config, caller-selected base time, or count.
- Capture one server UTC base time, then call the existing
  `next_run_at(expression, after=cursor)` helper five times, advancing the
  cursor after every result. Preserve Celery five-field parsing, Shanghai
  timezone conversion, and day/week AND behavior.
- Return exactly five ascending, timezone-aware UTC timestamps that are
  strictly later than `base_at`, plus the literal timezone marker
  `Asia/Shanghai` for client rendering.
- The router has no scheduler `Session` dependency and the service does not
  read or mutate jobs/runs, bind audit actors, publish Celery work, or expose
  dispatch-lease fields.
- The frontend generates this request after a 300ms page-local debounce of an
  editor Cron value. It hides stale results while input changes and renders
  current failures inline; it never treats preview data as saved `next_run_at`
  or authorization.
- Regenerate `frontend/src/client/**` through `scripts/generate-client.sh`
  after adding the OpenAPI response schema.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Caller has `scheduler.jobs.read` and submits a valid five-field Cron | Return 200 with one server-derived base and exactly five future values; write and publish nothing. |
| Caller lacks `scheduler.jobs.read` | Return unified 403 `detail + request_id`; do not infer authorization from page visibility. |
| Cron is empty, not five fields, or rejected by Celery | Convert it to unified 422 `detail + request_id` before any scheduler side effect. |
| Editor value changes during debounce or query | Hide the prior expression's result/error until the current value resolves. |
| Editor receives a current invalid-Cron response | Render the error inline without a global toast and without blocking the existing save flow. |

### 5. Good / Base / Bad Cases

- Good: an administrator types `0 8 * * *`; the server bases the response on
  its current UTC clock and the page displays five Shanghai 08:00 times without
  saving the form.
- Base: a saved job's editor opens with its existing Cron, but the preview is
  still calculated from the editor value rather than reusing stored
  `next_run_at`.
- Bad: querying a `job_id` and returning scheduler internals, adding a
  `count=1000` switch, letting the browser parse Cron, or creating a run while
  rendering a preview.

### 6. Tests Required

- Unit-test five iterations against a fixed server clock, strict-after-base
  behavior, Shanghai conversion, cross-month progression, and a day/week AND
  expression.
- API-test authorized success, invalid Cron 422, and missing read permission
  403. For every response, assert unchanged job/run rows, audit fields, and
  dispatch calls.
- Regenerate the client and compile the frontend to prove SDK/schema alignment.
- Browser-test an unsaved Cron's automatic 300ms preview, explicit Shanghai
  rendering, the five-value result, an inline invalid-Cron error, and removal
  of stale data after input changes.

### 7. Wrong Vs Correct

#### Wrong

```python
job = get_job(session=session, job_id=job_id)
return {"next_run_at": job.next_run_at}
```

The result cannot preview unsaved changes, is only one stored cursor, and
needlessly couples a read-only expression explanation to scheduler state.

#### Correct

```python
base_at = utc_now(now)
cursor = base_at
next_run_ats = []
for _ in range(5):
    cursor = next_run_at(cron_expression, after=cursor)
    next_run_ats.append(cursor)
```

The preview uses exactly the production Cron semantics while preserving a
side-effect-free boundary.

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

## Scenario: Generic Email Outbox

### 1. Scope / Trigger

- Trigger: an HTTP route, runtime task, or scheduler alert needs non-report
  email delivery. Inventory daily reports retain their dedicated delivery
  tables and are not migrated into this model.

### 2. Signatures

- Table: `email_outbox`, with `BIGINT GENERATED ALWAYS AS IDENTITY` id and
  audit fields.
- Tasks: `email_outbox.scan_due()` every minute and
  `email_outbox.deliver(outbox_id: int)`.
- Kinds: `RENDERED`, `ACCOUNT_SET_PASSWORD`, `PASSWORD_RECOVERY`; states:
  `PENDING`, `LEASED`, `RETRY_WAIT`, `DELIVERED`, `FAILED`.
- Producers: `queue_rendered_email(...)`,
  `queue_account_set_password_email(...)`, and
  `queue_password_recovery_email(...)`.

### 3. Contracts

- One row owns one scalar recipient. `RENDERED` stores a subject and HTML
  snapshot with no User reference. Link kinds store a User reference with no
  subject, HTML, initial password, or reset JWT.
- HTTP writes the outbox row in its request Unit of Work and never calls SMTP
  or Celery directly. The test-email route returns `202` with
  `Test email queued`.
- The scanner recovers expired leases, commits due IDs, then publishes each
  numeric ID. A worker claims in one transaction, calls SMTP outside it, then
  records the result in a new transaction only if its lease is still current.
- Retries are every 15 minutes with at most eight attempts. SMTP acceptance
  before worker loss can duplicate email but must not silently lose delivery.
- Link delivery re-reads the User and requires active, non-System status plus
  an unchanged email. Otherwise it records terminal `RECIPIENT_INVALID`.
- The initial human creator remains the audit actor for the first claim/result;
  retries, lease recovery, System-created rows, and terminal compensation use
  the System Actor.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| SMTP is unavailable | Keep the row and move it to `RETRY_WAIT` with `SMTP_NOT_CONFIGURED`. |
| SMTP send raises | Keep the row and move it to `RETRY_WAIT` with `SMTP_DELIVERY_FAILED`. |
| Delivery lease expires | System Actor moves it to `RETRY_WAIT`, or terminal `FAILED` on attempt eight. |
| Link User is missing, inactive, System, or has a different email | Mark `FAILED/RECIPIENT_INVALID`; do not send. |
| Row is `DELIVERED` or `FAILED` | Do not claim or send it again. |

### 5. Good / Base / Bad Cases

- Good: an active managed user creation writes an
  `ACCOUNT_SET_PASSWORD` row in the same commit; the worker creates a fresh
  reset-password token only in memory.
- Base: a scheduler alert locks and updates its throttle while creating one
  `RENDERED` row per configured recipient in that same transaction.
- Bad: placing a password or JWT in an outbox row, calling `send_email()` from
  an HTTP route, or passing HTML/User objects to Celery.

### 6. Tests Required

- Cover the migration round trip and database shape constraints.
- Cover one-time success, missing SMTP, provider failure, lease recovery,
  eight-attempt termination, and invalid link recipients.
- Cover active managed-user, password-recovery, test-email `202`, and scheduler
  producer boundaries; assert HTTP only persists rows.

### 7. Wrong Vs Correct

#### Wrong

```python
send_email(email_to=email, subject=subject, html_content=html)
```

This loses durable delivery progress if the request or scheduler process dies.

#### Correct

```python
queue_rendered_email(
    session=session, recipient=email, subject=subject, html_content=html
)
```

The request transaction persists the delivery intent before the minute scanner
hands only its numeric ID to Celery.

## Scenario: Inventory Correction Application Work Item

### 1. Scope / Trigger

- Trigger: an approved inventory-document correction must mutate the document
  and ledger asynchronously without treating at-least-once Celery delivery as
  permission to apply the correction twice.

### 2. Signatures

- Task: `inventory.document_correction.apply`, once per minute; it disables
  run-now and backfill.
- Tables: `inventory_correction_request`, `inventory_correction_work_item`,
  and `inventory_correction_attempt`.
- HTTP boundary: `POST /inventory/correction-requests/{id}/approve` creates
  one work item and its initial attempt; `POST
  /inventory/correction-work-items/{id}/recover` accepts an empty body.

### 3. Contracts

- Ordinary update, delete, and restore reject a ledger-affected document with
  `409 INVENTORY_CORRECTION_REQUIRED`; only the correction executor calls the
  internal inventory write path.
- Approval creates exactly one `PENDING` attempt. The scan locks and claims at
  most 20 pre-created attempts, records the scheduler-run ID, and never
  creates a new attempt while claiming.
- The executor locks the work item, attempt, request, and document in one
  transaction, checks the immutable proposal hash and expected `updated_at`,
  then commits the inventory/ledger mutation, success state, and semantic audit
  event together.
- A lease-expired `RUNNING` attempt is terminal `EXECUTION_LOST`. Domain or
  unexpected executor failures are terminal categories, not automatic retries.
  Recovery rechecks the target and proposal, rejects another active request,
  and appends exactly one new `PENDING` recovery attempt.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Direct write targets a ledger-affected document | Return unified 409; do not change document or ledger. |
| Approval sees a changed target timestamp | Persist `STALE`; create no work item or attempt. |
| A claimed attempt is redelivered or already terminal | Do nothing; no second ledger effect. |
| Lease expires before application commits | Mark `TERMINAL_FAILED/EXECUTION_LOST`; do not reapply automatically. |
| Recovery sees changed target/proposal or another active request | Return unified 409 and append no attempt. |

### 5. Good / Base / Bad Cases

- Good: approval creates a durable work item first, then the scheduler applies
  its single pending attempt under the System Actor.
- Base: a negative-balance proposal rolls back the inventory change and records
  `NEGATIVE_BALANCE` in a separate terminal-finalization transaction.
- Bad: enqueueing a raw proposal directly to Celery, creating an attempt on
  every scan, or retrying a terminal correction automatically.

### 6. Tests Required

- Cover direct-write blocking, self-review, duplicate approval, timestamp
  staleness, negative balance, lease loss, duplicate delivery, recovery, and
  audit-summary allowlists.
- Assert attempt count and ledger effects remain unchanged after a duplicate
  delivery or a rejected recovery.
- Run the correction API tests against `POSTGRES_DB=aiadmin_test`; regenerate
  the frontend client and verify the correction route/menu contract when its
  public schemas change.

### 7. Wrong Vs Correct

#### Wrong

```python
apply_correction.delay(request_id)
```

This makes broker redelivery a second business application opportunity.

#### Correct

```python
attempts = claim_pending_attempts(session=session, scheduler_run_id=run_id)
for work_item_id, attempt_id in attempts:
    apply_claimed_attempt(session=session, work_item_id=work_item_id, attempt_id=attempt_id)
```

The durable attempt is the one application opportunity; its terminal state is
the idempotency boundary.
