# Use Request-Scoped Unit Of Work For HTTP Writes

## Status

Accepted. This is the current transaction boundary for HTTP writes.

## Context

The item-specific rule in [ADR-0003](./0003-item-service-owns-transactions.md)
did not compose when a request changed several entities or queued durable side
effects. A request-scoped owner gives those changes one atomic outcome.

## Decision

HTTP write requests own one database transaction through `WriteSessionDep`: it
reuses the request-cached `get_db` session, commits after a successful
endpoint, and rolls back on any exception. `SessionDep` remains the primary
session dependency for authentication, RBAC, and reads that require
read-after-write consistency. An explicitly allowlisted pure business read that
accepts replication delay may use `ReadSessionDep`, which opens an independent
function-scoped session from `read_engine` and never explicitly commits, rolls
back, or drains cache invalidations. Services and CRUD helpers may `flush` or
`refresh` but must not commit or roll back. This supersedes the item-specific
transaction rule so multi-step HTTP commands are atomic without each service
inventing its own transaction boundary.

## Consequences

- Background tasks, CLI commands, startup, and migration work are outside the
  HTTP Unit of Work; they retain explicit, short transaction phases and must
  not hold database transactions across SMTP, HTTP, or Celery calls.
- Existing direct service callers outside HTTP must adopt an explicit
  transaction owner before their internal commits are removed.
- Every HTTP `POST`, `PUT`, `PATCH`, and `DELETE` endpoint uses
  `WriteSessionDep`, including endpoints that currently only authenticate or
  read. Authentication dependencies continue to use `SessionDep` and receive
  the same cached request session.
- `ReadSessionDep` is limited to the current pure-read allowlist in the
  inventory and scheduler modules. Its business-query session is deliberately
  separate from the primary `SessionDep` used by authentication and permission
  checks. When `POSTGRES_READ_REPLICA_SERVER` is unset, `read_engine` is the
  exact primary engine object; when it is configured, read failures remain
  observable and never silently retry against the primary. Replica-backed
  reads are eventually consistent and must not be used for write-following,
  correction-status, user, or permission queries.
- Services flush where they need generated identities or to translate an
  integrity error, but never commit or roll back; the Unit of Work owns the
  final transaction outcome.
- HTTP endpoints do not publish a Celery task before their transaction commits.
  Manual scheduler runs remain `QUEUED` and the existing scheduler scan
  dispatches them after commit.
- This is a platform boundary change; every HTTP write path and its tests must
  follow it before the old model is considered unavailable.

## Related Decisions

- [ADR-0003: Item Service Owns Transactions](./0003-item-service-owns-transactions.md) (deprecated)
- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0007: Require An Explicit Audit Actor](./0007-require-an-explicit-audit-actor.md)
- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)
