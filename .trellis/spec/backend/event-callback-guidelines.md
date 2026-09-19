# Event Callback Kernel Guidelines

This contract applies to `backend/app/modules/events/**`, the event models and
the Celery integration. It defines a durable internal callback kernel only. It
does not define business event adapters, Webhooks, dynamic subscriptions, or
HTTP routes.

## 1. Scope / Trigger

- Trigger: a trusted backend module needs to record an event in its existing
  transaction and invoke explicitly registered in-process handlers after
  commit.
- PostgreSQL `event_publication` and `event_delivery` are the execution facts.
  Redis/Celery carries only a positive integer delivery ID.
- The kernel is at-least-once. It does not provide global ordering, exactly-once
  handler execution, tenant isolation, automatic retention, or replay.

## 2. Signatures

- `publish_event(*, session: Session, envelope: EventEnvelope) -> EventPublication`
  adds and flushes facts but never commits or rolls back the caller's session.
- `handler(envelope: EventEnvelope) -> None` is the only handler protocol.
  Normal return succeeds; `PermanentEventError` is terminal rejection; other
  `Exception` values become `HANDLER_EXECUTION_FAILED`.
- Celery tasks are `events.scan_due_deliveries() -> None` and
  `events.process_delivery(delivery_id: int) -> None`. Task payloads must not
  contain the event envelope or a business identifier.
- `EventDeliveryState` is `PENDING`, `LEASED`, `RETRY_WAIT`, `SUCCEEDED`, or
  `FAILED`. Error categories are the closed set:
  `HANDLER_NOT_REGISTERED`, `HANDLER_EVENT_TYPE_MISMATCH`,
  `SCHEMA_VERSION_UNSUPPORTED`, `HANDLER_REJECTED`,
  `HANDLER_EXECUTION_FAILED`, and `EXECUTION_LEASE_EXPIRED`.

## 3. Contracts

- `EventEnvelope` is frozen, rejects unknown top-level fields, requires a UUID
  `event_id`, positive `schema_version`, timezone-aware `occurred_at`, and a
  strict JSON object payload.
- Payload validation uses canonical UTF-8 JSON of at most 65,536 bytes and at
  most 32 container levels. Reject non-finite numbers, non-string keys,
  arbitrary objects, bytes, implicit dates, and cycles. Copy the payload before
  persistence and before each handler invocation.
- `event_id` is the only publication deduplication key. Same ID and business
  semantics returns the original publication; a different semantic payload is
  `EventPublicationConflict`. `request_id` and `trace_id` are retained from
  the first publication but do not cause a retry conflict.
- Matching is exact on `event_type` and supported schema version. The registry
  is code-owned; duplicate keys, invalid declarations, dynamic imports and
  database-configured callables are forbidden. A publication freezes matching
  handler keys; later registrations do not backfill it.
- Publication, delivery rows and publication audit are one caller transaction.
  Delivery state changes and their `AuditEvent` are one worker transaction.
  The caller/first attempt keeps `created_by`; automatic retry and recovery use
  the System Actor. Missing Actor context fails closed.
- Dispatch lease (`next_dispatch_at`) and execution lease
  (`lease_token`/`lease_expires_at`) are separate. Scan at most 100 due rows
  with `FOR UPDATE SKIP LOCKED`, commit the dispatch reservation, then enqueue
  one delivery ID. Sending failure conditionally releases the exact old
  dispatch reservation without incrementing `attempt_count`.
- Execution increments `attempt_count` on claim, accepts a result only while
  state, token, and lease expiry match, retries ordinary failures after 15
  minutes, and stops at 8 attempts. A stale or duplicate result is a no-op.
- Never read an expired SQLAlchemy result object after its session commits.
  Capture stable scalar state before commit if post-commit logging is needed.
  Coordinator exceptions must be replaced with fixed text and must not retain
  the original exception chain.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Uncommitted caller transaction | Worker cannot see or execute the event |
| Same `event_id` and same semantics | Return the original row; no new delivery or audit |
| Same `event_id` and different semantics | Raise `EventPublicationConflict`; preserve caller transaction via savepoint |
| Payload, context, or registration invalid | Reject before durable event facts; expose no raw input in logs |
| No matching handler at publication | Persist publication only; never backfill after registration |
| Missing handler key at Worker | `FAILED` + `HANDLER_NOT_REGISTERED`; handler not called |
| Handler key maps to another `event_type` | `FAILED` + `HANDLER_EVENT_TYPE_MISMATCH`; handler not called |
| Unsupported schema version | `FAILED` + `SCHEMA_VERSION_UNSUPPORTED`; handler not called |
| Ordinary handler exception | `RETRY_WAIT` until attempt 8, then `FAILED` |
| Lease token mismatch or expired result | No state change and no semantic audit |
| Database/audit commit failure | Transaction rolls back; handler result is not declared durable |

## 5. Good / Base / Bad Cases

- Good: a business service creates `EventEnvelope`, calls `publish_event` in
  its own transaction, commits its business row and the event together, and
  lets the scanner enqueue the persisted delivery ID.
- Base: a handler performs its own durable side effect idempotently by
  `event_id` or its business key, then returns `None`; the kernel records
  `SUCCEEDED` separately.
- Bad: a worker sends the full payload through Celery, imports a dotted path
  from the database, or treats broker acknowledgement as successful execution.
- Bad: a task commits a state transition and then dereferences an expired ORM
  instance to decide which log event to emit. Read the scalar before commit.

## 6. Tests Required

- Contract tests: strict JSON, byte/depth limits, frozen/deep-copy behavior,
  unknown fields, timestamp/context validation, and duplicate registration.
- Database tests: migration comments/enums/constraints, publication
  idempotency and conflict savepoint behavior, audit atomicity, Actor
  attribution, bounded dispatch claims, stale token no-op, retry 8th-attempt
  terminal behavior, and event-type mismatch classification.
- Runtime test: isolated PostgreSQL plus an independent Redis and real Celery
  worker must prove persisted publication -> delivery -> handler -> audit.
  Eager execution is not evidence for broker or worker recovery.
- Regression gate: run `backend/scripts/lint.sh` and the affected
  EmailOutbox/Scheduler/Celery tests. Do not run destructive downgrade against
  a database containing event facts.

## 7. Wrong vs Correct

### Wrong

```python
result = fail_delivery(...)
session.commit()
if result.state.value == "RETRY_WAIT":
    log_event(event_name="event.delivery.retry_wait", severity="ERROR")
```

`Session.commit()` expires the ORM instance. The log decision can raise
`DetachedInstanceError` after the durable failure has already been written.

### Correct

```python
result = fail_delivery(...)
failure_state = result.state.value if result is not None else None
session.commit()
if failure_state == "RETRY_WAIT":
    log_event(event_name="event.delivery.retry_wait", severity="ERROR")
```

The transaction remains the source of truth, and post-commit logging uses only
a stable scalar captured before the session closes.
