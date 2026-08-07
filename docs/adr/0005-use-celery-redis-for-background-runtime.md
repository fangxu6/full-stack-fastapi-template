# Use Celery And Redis For Background Runtime

## Status

Accepted. Celery and Redis remain the shared background runtime, with distinct
Redis roles and PostgreSQL as the business source of truth.

## Context

The original bootstrap plan covered only a diagnostic `runtime.ping` task and
used Redis for the broker and short-lived task results. The runtime has since
grown to include durable outbox delivery, scheduler, audit, and inventory
tasks, and configuration now exposes a separate Redis cache URL.

## Decision

Celery with Redis is the shared background-task runtime. Redis roles remain
separated: database 0 is the broker, database 1 is the short-lived Celery
result backend, and database 2 is the application cache. Key namespaces and
clients remain separated by those role-specific URLs. Redis is not a business
data store; durable task and delivery state belongs in PostgreSQL before work
is published.

Workers use the existing late-acknowledgement and visibility-timeout contract,
so business tasks must be idempotent. Task arguments remain JSON-serializable
identifiers or bounded values, never ORM instances or credentials.

The initial `runtime.ping`-only scope is historical. Current registered work
also includes outbox, scheduler, audit, and inventory tasks; each retains its
own approved persistence and retry rules.

## Considered Options

- Keep Redis limited to the broker and short-lived task results: this was the
  original bootstrap scope but does not describe the separate configured cache.
- Use Redis as a business data store: rejected because PostgreSQL owns durable
  business facts and audit history.
- Replace Celery with a different worker runtime: rejected because the current
  deployment, task contracts, and tests already use Celery.

## Consequences

- Workers use late acknowledgement, so business tasks must be idempotent.
- Redis outages do not erase PostgreSQL business facts; dispatch and retry
  behavior is governed by durable records and the relevant ADRs.
- Task arguments remain JSON-serializable identifiers or bounded values, never
  ORM instances or credentials.

## Related Decisions

- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)
- [ADR-0013: Restrict Detailed Celery Task-Failure Logging](./0013-restrict-detailed-celery-task-failure-logging.md)
