# Require An Explicit Audit Actor

## Status

Accepted. Explicit actor binding is required for every `AuditFields` write.

## Context

Audited records need attribution that survives HTTP, Celery, CLI, bootstrap,
and scheduler boundaries. Logging context is not a durable or sufficient audit
source, and silently falling back to a system identity hides missing caller
propagation.

## Decision

Every `AuditFields` write must identify an actor explicitly: the authenticated
human User that initiated it, or a protected System Actor when an automated
process has no human initiator. HTTP requests bind the human actor to their
Session and the ORM audit hook sets `created_by`, `updated_by`, and timestamps;
it rejects attempts to change `created_by`. Background tasks, CLI commands, and
bootstrap work must explicitly select their human actor or System Actor; the
hook never supplies either implicitly.

## Consequences

- A missing audit actor is a failed write, not a null value or an automatic
  fallback.
- The audit hook reads the actor only from the current SQLAlchemy Session's
  `info`; HTTP, Celery, CLI, and bootstrap code bind the actor to their own
  Session explicitly. Operational logging context is not an audit source.
- On insertion the hook sets all four creation and update values. On later
  changes it sets `updated_at` and `updated_by`, and rejects any change to
  persisted `created_at` or `created_by`; domain soft-delete state remains a
  normal mutable field.
- System Actors are application-seeded or explicitly provisioned, non-loginable
  Users with no roles. Private `User.is_system_actor` and non-null
  `system_actor_key` identify them; a database check constraint keeps keys off
  ordinary users and a partial unique index guarantees at most one actor per
  key. Initialization creates the default `system` key idempotently with
  display address `system@example.com`, a random unusable password, and no
  fixed UUID. A controlled provisioning command creates additional keys from
  explicit key and display-email inputs. The marker and key, not the address,
  are the identity.
- User-management and role-assignment operations must not modify or delete any
  System Actor.
- Every System Actor is excluded from user lists and direct user reads. It is
  an audit attribution target, not a user-management resource.
- Automated work uses a System Actor only when no human initiated the action.
  It cannot replace correctly propagating a human actor through asynchronous
  work. CLI import may select either an active human or a pre-provisioned
  System Actor; it rejects a missing or inactive human actor.
- A persisted initiating User, such as a manual scheduler run's
  `requested_by`, remains the actor for its later asynchronous writes;
  scheduled runs, retries, registration, password recovery, and other
  no-authentication entry points use the default `system` key.
- The scheduler resolves that actor before invoking a task and passes only its
  UUID in `ScheduledTaskContext.actor_id`; each task binds the UUID to every
  Session it opens. It does not pass a detached User instance or reload the
  SchedulerRun merely to recover attribution.
- HTTP write services no longer set audit fields themselves; the ORM hook is
  the only HTTP write path for those fields.
- User registration and other entities that do not inherit `AuditFields` are
  unaffected.

## Related Decisions

- [ADR-0004: Use BIGINT Identity For New Entity Primary Keys](./0004-use-bigint-identity-for-new-entity-primary-keys.md)
- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)
