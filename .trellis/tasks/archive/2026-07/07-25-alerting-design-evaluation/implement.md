# Alerting Implementation Plan

## Current Task

No production code is implemented by this design task. There is no concrete
business event to validate, so adding an empty interface or idle Celery stack
would create unowned infrastructure.

## Prerequisites For The First Alert Task

- Name one stable `event_code`, its owning module, trigger condition, severity,
  threshold if timed, primary on-call target, email fallback target, cooldown,
  retry limit, and retention period.
- Confirm the alert body fields are safe for the selected IM and email targets.
- Create a new task that references this design and has its own PRD, migration,
  delivery validation plan, and operational runbook.

## Future Execution Checklist

1. Add bounded Celery Redis dependencies and validated settings; add Redis,
   Celery worker, and Celery Beat services to both Compose deployment shapes.
2. Create typed `modules/alerting` contracts, service, repository, task entry
   points, and Webhook/email adapters. Keep route handlers out of the path
   unless a real administrative API is separately approved.
3. Add `alert_outbox`, `alert_delivery`, and `alert_throttle` models plus an
   Alembic migration. Document the operational-table audit-field exception and
   use the `alert_` database namespace.
4. Have the owning business service add an alert intent in its existing
   transaction. Enqueue only after successful commit; queue only an outbox or
   delivery ID.
5. Implement leasing, idempotent state transitions, bounded timeouts,
   backoff, Beat recovery scans, primary-webhook routing, and email fallback.
6. Add safe alert-delivery telemetry through an explicitly reviewed extension
   to the closed observability event contract; never log bodies, provider
   responses, recipients, URLs, or credentials.
7. Add focused tests for dedupe, throttle concurrency, post-commit enqueue
   loss recovery, retry exhaustion, duplicate Celery execution, fallback
   routing, and redaction. Use task eager mode only for narrow unit tests and
   run at least one worker/broker integration test in an isolated environment.
8. Update deployment/runbook documentation with secret configuration, worker
   and Beat health checks, backlog inspection, failed-delivery recovery, and
   rollback order.

## Validation

- `bash backend/scripts/lint.sh`
- Focused backend tests for alerting and the owning business module.
- An isolated PostgreSQL + Redis integration run covering outbox persistence,
  duplicate task delivery, retry, and fallback behavior.
- No OpenAPI/client generation is needed unless a future task adds an alert
  administration or user-notification API.

## Rollback Points

- Do not enable a business trigger until Redis, worker, Beat, and a test
  channel have passed staging validation.
- Disable the trigger before stopping workers or Beat.
- Preserve PostgreSQL outbox/delivery rows through the approved retention
  period; Redis is a disposable execution transport, not the source of truth.
