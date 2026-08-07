# Use A Generic Email Outbox For Non-Report Mail

## Status

Accepted. Generic non-report mail uses the durable PostgreSQL outbox; report
delivery remains inventory-owned.

## Context

Welcome mail, password recovery, test mail, and scheduler alerts need durable
request state, retry behavior, and actor attribution. Inventory daily reports
also have report-specific recipient resolution, aggregation, and completion
state that do not belong in a generic delivery row.

## Decision

Welcome mail, password-recovery mail, test mail, and scheduler alerts are
persisted in a generic `email_outbox` before delivery by Celery.
`InventoryDailyReportDelivery` remains the inventory module's report-specific
delivery model. Scheduler alert throttling is evaluated independently per
`SchedulerJob` and alert category, with the existing one-hour window; one job's
failure or unsent alert does not consume another job/category's allowance.

## Consequences

- The generic worker receives only an outbox identifier, claims a durable row,
  sends SMTP outside the transaction, then records the result in a new
  transaction.
- HTTP endpoints no longer synchronously guarantee SMTP acceptance; they
  guarantee that the durable delivery request was created with their business
  change.
- `EmailOutbox` is an audited BIGINT-identity row with one recipient per row.
  Its fixed kinds are `RENDERED`, `ACCOUNT_SET_PASSWORD`, and
  `PASSWORD_RECOVERY`; rendered mail stores its recipient, subject, and HTML
  snapshot, while link mail stores only recipient and User references. It has
  no class-path or arbitrary JSON rendering protocol.
- Outbox data must not retain a plaintext initial password or password-reset
  JWT. New-account mail uses the existing password-reset flow as a set-password
  link; the worker generates its short-lived link at send time from the queued
  User reference, so a retry may send a fresh link.
- A managed User receives the initial set-password outbox row only when created
  active. Creating a disabled User, or enabling one later, never implicitly
  sends an invitation.
- Password recovery creates an outbox row only for an active non-System-Actor
  User; unknown, inactive, and System Actor identities return the same
  enumeration-safe response without a delivery record.
- Before rendering a link mail, the worker rechecks that its referenced User is
  active, is not the System Actor, and still has the queued recipient email.
  Any mismatch is terminal `RECIPIENT_INVALID`, without sending or retrying.
- SMTP availability does not decide whether a valid delivery request becomes an
  outbox row. The worker records `SMTP_NOT_CONFIGURED` and follows the normal
  retry policy; missing scheduler alert recipients remain the only case that
  produces no alert outbox row.
- Scheduler alerting locks the Job, applies the per-job/per-category one-hour
  throttle, advances that throttle timestamp, and inserts one rendered outbox
  row per configured recipient in the same transaction. With no recipients, it
  inserts none but still advances the throttle and emits one
  `scheduler.alert.unsent` event per job/category/hour.
- An authenticated creator remains the audit actor for the first delivery
  attempt and its result. Outbox rows created without a human actor, and every
  retry, lease recovery, and terminal compensation, use the System Actor.
- Delivery permits eight total attempts, retries every 15 minutes, and uses the
  existing Celery visibility timeout as its lease. Terminal failure stays
  recorded as `FAILED`; no global business retry is introduced.
- Initial delivery history has no automatic cleanup or content purge; an
  explicit retention requirement is needed before adding one.
- Celery Beat scans due outbox rows every minute; HTTP requests never enqueue
  directly. The worker receives only an outbox ID after the durable row has been
  committed, removing the commit/enqueue race at the cost of at most one
  minute of dispatch latency.
- The existing 09:00 runtime test-email task remains, but creates a System-Actor
  `RENDERED` outbox row; it no longer calls SMTP directly.
- The authenticated test-email endpoint returns `202 Accepted` and
  `"Test email queued"`; existing welcome and password-recovery response
  contracts remain successful once their durable outbox row has been written.
- The outbox has no management API or frontend page in this delivery. It is
  observed through its durable state, safe task logs, and existing SMTP failure
  events.
- A future non-report email producer reuses `email_outbox`; it must not add
  another ad hoc SMTP retry model.

## Related Decisions

- [ADR-0004: Use BIGINT Identity For New Entity Primary Keys](./0004-use-bigint-identity-for-new-entity-primary-keys.md)
- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0007: Require An Explicit Audit Actor](./0007-require-an-explicit-audit-actor.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)
