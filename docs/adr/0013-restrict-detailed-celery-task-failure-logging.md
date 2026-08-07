# Restrict Detailed Celery Task-Failure Logging

## Status

Accepted. This ADR supersedes the task-exception prohibition in
[ADR-0010](./0010-use-safe-celery-task-observability-context.md) while keeping
its validated task-context and cleanup rules.

## Context

The current Celery failure boundary deliberately preserves an original
exception and traceback for operations. The `task_failure` signal calls the
restricted `log_exception()` facade, which emits a structured `task.failed`
event to the stdout NDJSON sink. This is a reviewed operational path, not a
general permission for application modules to log arbitrary exceptions or
business context.

## Decision

- Only the unhandled Celery `task_failure` boundary may pass the original task
  exception and traceback to `log_exception()` for the structured `task.failed`
  event. There is one failure event for a failure that has valid, prerun-bound
  task context.
- The event may include the already validated canonical `task_id` and
  registered `task_name` context. It may include the exception and traceback
  supplied by Celery at that boundary.
- Task arguments and keyword arguments, signal headers, return values,
  recipients, user or resource identifiers, credentials, tokens, and arbitrary
  context are prohibited. Signal payload extensions may be accepted only as
  opaque compatibility data and must not be read or serialized.
- `log_event()` remains the closed safe facade for ordinary application events.
  The HTTP middleware's `http.request.failed` path and this Celery
  `task_failure` boundary are the only reviewed `log_exception()` call sites.
  Application code must not call a logger directly or add another
  `log_exception()` call site without a new reviewed decision.
- The application writes the event to the existing structured stdout sink. The
  operations owner controls collector access, retention, export, and deletion
  policy; this ADR does not grant application users access to raw task
  tracebacks or make the collector a business-data store.
- Redaction and access controls remain mandatory at the collector and
  operations boundary. A task must not intentionally place sensitive or
  business identifiers in its exception message merely because this boundary
  preserves the original exception.

## Consequences

- Operators can diagnose unexpected task failures with the original traceback
  while retaining canonical task correlation.
- The exception path is intentionally narrower than ordinary event logging and
  is not available to task business code as an arbitrary telemetry channel.
- Collector retention and reader permissions are operational controls and must
  be reviewed with deployment and incident-response policy.
- Durable task, scheduler, and delivery state remains in PostgreSQL; logging
  cannot replace those records.

## Related Decisions

- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
- [ADR-0010: Use Safe Celery Task Observability Context](./0010-use-safe-celery-task-observability-context.md) (exception-detail prohibition superseded; context and cleanup remain accepted)
