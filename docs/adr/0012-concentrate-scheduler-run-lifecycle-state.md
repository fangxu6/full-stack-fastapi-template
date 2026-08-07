# Concentrate Scheduler Run Lifecycle State

## Status

Accepted. This ADR records the implemented refactoring shape; implementation
was separately approved through the scheduler lifecycle task.

## Context

The scheduler intentionally has two runtime phases:

- Celery Beat scans due `SchedulerJob` definitions and publishes a numeric
  `SchedulerRun` identifier.
- A Celery Worker claims that identifier and executes the frozen task snapshot.

These phases are not duplicate business execution. The durable run record is
created before dispatch so PostgreSQL remains the source of truth and a broker
failure does not erase the business fact.

Before this refactoring, lifecycle transitions were spread between
`service.py` and `tasks.py`. That made status, lease, retry, and terminal-state
changes easy to update inconsistently. The current implementation has moved
durable transitions into `run_lifecycle.py`; `service.py` delegates to it,
`orchestration.py` coordinates Beat/Worker dispatch, and `tasks.py` is a thin
Celery registration adapter.

## Decision

Keep the Beat/Worker producer-consumer split, but concentrate durable
`SchedulerRun` lifecycle state in the scheduler-owned `run_lifecycle.py`
module.

The lifecycle module owns all persistence transitions and invariants for:

- creating a frozen run snapshot;
- claiming and releasing the dispatch lease;
- claiming execution and reclaiming an expired execution lease;
- cancelling queued runs;
- recording successful, skipped, and failed terminal states;
- clearing lease fields and recording completion timestamps; and
- deleting eligible historical runs.

`service.py` remains responsible for `SchedulerJob` definitions, CRUD, Cron
validation, task configuration validation, and manual-operation validation. It
delegates run persistence to the lifecycle module. `orchestration.py` owns
scanning due jobs, publishing `scheduler.execute_run(run_id)` after a durable
lease claim, and coordinating the Beat/Worker handoff. `tasks.py` registers the
Celery entrypoints and delegates frozen execution and result classification to
the scheduler execution/lifecycle helpers.

`scheduler/execution.py` owns the side-effect-free execution boundary. It
resolves the frozen task class, validates the frozen configuration, invokes
`ScheduledTask.run()`, and returns a `SchedulerRunOutcome`. It does not open a
database session, write run state, or send alerts. `run_lifecycle.py` converts
that outcome into the durable terminal state through `finish_outcome()`.

The lifecycle module must not publish Celery messages, send SMTP, or own
business-task execution. It must not introduce a second `ScheduledTask`
interface or a generic state-machine framework.

All lifecycle writes must keep the existing transaction rules. HTTP writes
remain owned by the request-scoped unit of work. Beat, Worker, cleanup, and
other background callers retain short explicit transaction phases and must not
hold a database transaction across Celery or email operations.

## Consequences

- `SchedulerRun` status, lease, retry, and terminal-state rules have one
  locality and one focused test surface.
- Beat and Worker remain independently scalable and failure-isolated; this
  decision does not merge them into one executor.
- At-least-once delivery, the default Celery queue, PostgreSQL source of truth,
  and business-task idempotency remain unchanged.
- The scheduler service and Celery task entrypoints become thinner without
  changing public scheduler schemas or generated frontend clients.
- Existing alert throttling and `EmailOutbox` persistence remain governed by
  ADR-0009; this ADR does not create a second mail-delivery model.
- A lease or terminal-state change must update lifecycle tests and scheduler
  task integration tests together.

## Non-Goals

- Merging Celery Beat and Worker execution.
- Executing business tasks directly from an HTTP request.
- Adding a new queue, generic retry engine, scheduler status, migration, or
  public lifecycle API.
- Rewriting the scheduler as Clean Architecture, microservices, or a generic
  workflow engine.

## Related Decisions

- [ADR-0002: Evolve Backend as a Modular Monolith](./0002-evolve-backend-as-modular-monolith.md)
- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0007: Require An Explicit Audit Actor](./0007-require-an-explicit-audit-actor.md)
- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
