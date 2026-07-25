# Alerting Design Evaluation

## Decision

Define a channel-neutral alert contract now. Do not add an empty Python
interface, Celery, Redis, database tables, environment variables, or channel
adapters until an approved business event needs them.

The first real alert implementation will use a focused `alerting` module with
Celery + Redis for execution and a PostgreSQL outbox for durable business
facts. This is an at-least-once delivery design, not an exactly-once promise.

## Problem And Scope

Future important business conditions and approved business timeouts need to
notify an accountable on-call group without coupling business services to a
specific IM provider. Webhook delivery is the primary path; email is a
fallback. Application-user work notifications are a different capability.

There is no owned event, threshold, recipient, or response policy today. An
uninvoked runtime cannot be tested end-to-end, so it is deliberately deferred.

## Recommended Boundary

```text
future business service
  -> AlertPublisher.emit(intent) in the business transaction
  -> PostgreSQL alert_outbox + alert_delivery rows
  -> post-commit Celery enqueue (outbox ID only)
  -> Redis broker -> Celery worker -> selected AlertNotifier
  -> primary Webhook channel -> optional email fallback

Celery Beat -> scans pending, expired-lease, and retryable outbox rows
```

`AlertPublisher` owns intent validation, deduplication, throttling, and
durable outbox creation. It does not make network calls. `AlertNotifier`
owns one provider-specific delivery. Business services only create an intent;
they never select a webhook URL, email recipient, or retry policy.

The future module belongs under `backend/app/modules/alerting/` because it
combines a durable work item, external calls, asynchronous execution, and
cross-module collaboration. It is not a general user-notification center.

## Contract

The first implementation should create typed models equivalent to the
following contract. This is a design signature, not code to add now.

```python
class AlertSeverity(StrEnum):
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertChannel(StrEnum):
    EMAIL = "email"
    WECOM = "wecom"
    FEISHU = "feishu"
    DINGTALK = "dingtalk"
    IN_APP = "in_app"


@dataclass(frozen=True)
class AlertIntent:
    event_code: str
    source: str
    severity: AlertSeverity
    title: str
    body: str
    fingerprint: str
    occurred_at: datetime
    request_id: str | None = None
    action_url: str | None = None


class AlertPublisher(Protocol):
    def emit(self, *, session: Session, intent: AlertIntent) -> None: ...


class AlertNotifier(Protocol):
    channel: AlertChannel

    def deliver(self, *, delivery_id: int) -> None: ...
```

`event_code` is a stable ASCII dotted code owned by the business scenario,
for example `inventory.import.failed`; it is never inferred from an exception
class. `source` identifies the owning bounded module. `fingerprint` is a
deterministic, non-sensitive identifier for one alert condition. The publisher
derives its storage deduplication key from `event_code + fingerprint`.

No free-form request data, response data, exception text, credentials, raw
webhook URLs, recipient addresses, tokens, or arbitrary ORM values may be put
in an intent. `action_url`, when approved for a future event, must be an
internal application URL without credentials or secret query parameters.

`in_app` remains in the enum for forward compatibility but has no first-phase
adapter, database model, API, or UI. The deployment selects one primary IM
channel; it must not broadcast to WeCom, Feishu, and DingTalk by default.

## Future Persistence And Delivery

The first implementation requires three alert-owned PostgreSQL tables. They
are operational delivery records, not business audit records, and must use an
explicitly reviewed exception to user audit fields because alerts may be raised
by system work with no authenticated User. They still use UTC timestamps and
the `alert_` namespace required for a module-owned durable object.

| Table | Purpose | Minimum fields |
| --- | --- | --- |
| `alert_outbox` | Durable intent and dispatch source of truth | intent snapshot, dedupe key, created time, lease/status, request ID when present |
| `alert_delivery` | One primary/fallback channel attempt history | outbox ID, channel, target reference, status, attempt count, next attempt, safe failure category |
| `alert_throttle` | Atomic cooldown ownership for a dedupe key | dedupe key, next allowed time, last outbox ID |

Within the business transaction, `emit()` acquires/updates the throttle row and
creates an outbox row only when the cooldown allows it. The business service
owns the commit. Post-commit enqueue is best effort: failure leaves the outbox
row discoverable by Beat. A Celery task receives only the numeric outbox or
delivery ID, opens its own session, and atomically claims work with a lease.

Delivery transitions are `PENDING -> DELIVERING -> DELIVERED`, or
`PENDING/DELIVERING -> RETRY_WAIT -> DELIVERING`, ending in `FAILED` after the
configured retry limit. A lease expiry returns interrupted work to a scan.
The sender must use bounded HTTP and SMTP timeouts and an exponential retry
schedule. The exact retry count, delay, cooldown, and retention are selected
with the first business event rather than invented now.

External side effects cannot be made exactly once: a worker can successfully
call an IM provider and crash before persisting `DELIVERED`. The system must
therefore tolerate a repeated provider message, include a stable alert ID in
the message, and treat database delivery history as the authoritative record.

## Routing And Security

The future startup configuration maps an approved event/severity route to one
primary IM channel and an optional email fallback. A missing primary target is
a configuration error for that event; provider credentials stay only in
deployment secrets and are never stored in PostgreSQL or Redis.

An email fallback is scheduled only after the primary channel reaches terminal
failure, so normal alerts do not generate duplicate group and email noise.
Future multi-group fan-out or per-user preferences require a separate routing
and notification-center design.

Alert delivery may create a separate, allowlisted operational record containing
only stable alert ID, event code, source, severity, channel, status, attempt,
and request ID. It must not pass the intent body or provider response through
the current closed `app.core.observability.log_event()` interface. The first
implementation must review and extend that observability contract explicitly.

## Mature Options

| Option | Best for | Decision |
| --- | --- | --- |
| Application module + PostgreSQL outbox + Celery/Redis | Owned business exceptions and business timeouts that need delivery history and provider-neutral adapters | Chosen for the first real business alert. |
| Prometheus Alertmanager | Infrastructure/metric alerts such as error-rate, availability, saturation, and latency aggregation | Add later outside the application; it complements rather than replaces business outbox alerts. |
| Novu or similar notification orchestration platform | High-volume, user-facing multi-channel notifications, templates, preferences, and in-app inbox | Defer; it adds an external platform and Chinese IM providers still need webhook/custom-provider work. |

## Explicitly Deferred

See [deferred-iterations.md](./deferred-iterations.md). In particular, this
design does not ship an alert event, adapter, Celery/Redis service, in-app
notification, acknowledgement, escalation, recovery notice, dynamic rule
management, or UI.

## Rollout And Rollback For The First Event

Deploy Redis, worker, Beat, and database migration before enabling the event
trigger. Validate a test channel and a forced provider failure in staging.
Rollback disables the triggering rule first, then workers/Beat; retain outbox
and delivery records until their approved retention period expires so no
in-flight history is lost. Redis may be flushed only after no outbox row can
be re-enqueued from it.
