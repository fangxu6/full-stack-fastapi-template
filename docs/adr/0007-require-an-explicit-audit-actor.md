# Require An Explicit Audit Actor

Every `AuditFields` write must identify an actor explicitly: the authenticated human User that initiated it, or the single protected System Actor when an automated process has no human initiator. HTTP requests bind the human actor to their Session and the ORM audit hook sets `created_by`, `updated_by`, and timestamps; it rejects attempts to change `created_by`. Background tasks, CLI commands, and bootstrap work must explicitly select their human actor or System Actor; the hook never supplies either implicitly.

## Consequences

- A missing audit actor is a failed write, not a null value or an automatic fallback.
- The audit hook reads the actor only from the current SQLAlchemy Session's `info`; HTTP, Celery, CLI, and bootstrap code bind the actor to their own Session explicitly. Operational logging context is not an audit source.
- On insertion the hook sets all four creation and update values. On later changes it sets `updated_at` and `updated_by`, and rejects any change to persisted `created_at` or `created_by`; domain soft-delete state remains a normal mutable field.
- The System Actor is a single application-seeded, non-loginable User with no roles. A private `User.is_system_actor` marker and database partial unique index identify it and guarantee exactly one row; initialization creates it idempotently with display address `system@example.com`, a random unusable password, and no configuration or fixed UUID. The marker, not the address, is its identity.
- User-management and role-assignment operations must not modify or delete the System Actor.
- The System Actor is excluded from user lists and direct user reads. It is an audit attribution target, not a user-management resource.
- Automated work uses the System Actor only when no human initiated the action. It cannot replace correctly propagating a human actor through asynchronous work.
- A persisted initiating User, such as a manual scheduler run's `requested_by`, remains the actor for its later asynchronous writes; scheduled runs, retries, registration, password recovery, and other no-authentication entry points use the System Actor.
- The scheduler resolves that actor before invoking a task and passes only its UUID in `ScheduledTaskContext.actor_id`; each task binds the UUID to every Session it opens. It does not pass a detached User instance or reload the SchedulerRun merely to recover attribution.
- HTTP write services no longer set audit fields themselves; the ORM hook is the only HTTP write path for those fields.
- User registration and other entities that do not inherit `AuditFields` are unaffected.
