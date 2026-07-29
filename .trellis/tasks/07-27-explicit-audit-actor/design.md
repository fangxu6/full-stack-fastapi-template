# Technical Design

## Scope And Boundaries

This task centralizes attribution only for the eight existing models that inherit
`AuditFields`. `User`, `Item`, `SchedulerRun`, `InventoryDailyReport`, and
`InventoryDailyReportDelivery` retain their current fields and behavior.

`WriteSessionDep` remains the generic HTTP transaction owner from ADR-0006. It
must not fabricate a System Actor for login, registration, password recovery, or
other non-audited writes. A second authenticated dependency is used only by
inventory and scheduler mutations that can write an `AuditFields` entity.

## System Actor And Migration

`User` gains private `is_system_actor: bool = False` and
`system_actor_key: str | None = None` persistence fields; no create, update, or
public-response schema contains either field. One Alembic revision:

1. adds the non-null marker with a false default and nullable key for existing
   rows;
2. adds a check constraint requiring a non-empty key exactly when the marker is
   true;
3. adds a PostgreSQL partial unique index for `system_actor_key` where the
   marker is true; and
4. does not add an actor row in migration SQL.

`system_actor_key` is the stable, non-human identity. Application initialization
owns only the default key `system`: `ensure_system_actor(session)` returns that
row or creates it with display email `system@example.com`, an unretained random
password hash, `is_active=False`, `is_system_actor=True`, and no roles. A
provisioning command creates or returns a custom System Actor from an explicit
key and display email; it never exposes the account through user-management
routes. Both paths use the database key constraint as the final concurrency
guard. A normal database uniqueness failure remains a startup failure or command
failure; this task adds no automatic data-repair flow.

`init_db()` calls the default initializer before it creates or modifies bootstrap
`SchedulerJob` records. A System Actor itself is a `User`, so its creation is
outside the audit hook. `require_system_actor(session)` resolves only the default
`system` key for scheduler boundaries and fails closed if that invariant is
absent. CLI import instead receives an existing actor UUID and permits either an
active human or a protected System Actor.

The migration and hook are forward-only once any audit record references any
System Actor. A normal downgrade must not remove the marker, key constraint,
unique index, or referenced account after use; recovery is a forward fix or
database backup restore. Upgrade/downgrade tests run only against the isolated
`aiadmin_test` database before an audit reference is created.

## Session Actor Contract

The audit subsystem exposes a narrow helper boundary around the current
SQLAlchemy Session:

```python
AUDIT_ACTOR_SESSION_KEY = "audit_actor_id"

def bind_audit_actor(*, session: Session, actor_id: UUID) -> None: ...
def require_system_actor(*, session: Session) -> UUID: ...  # key="system"
```

`bind_audit_actor` validates that `actor_id` names an existing `User` in the
same Session, then stores only that UUID in `Session.info`. It deliberately
allows the inactive System Actor and does not require a detached `User` object.
No request object, contextvar, logger context, global current-user state, or
Celery argument becomes an implicit audit source.

A SQLAlchemy `Session.before_flush` listener inspects only new entities and
dirty entities with scalar changes. For every `AuditFields` instance it:

- requires a valid UUID from `Session.info`;
- on insert, overwrites `created_at`, `created_by`, `updated_at`, and
  `updated_by` with one UTC instant and the bound actor;
- on update, rejects history changes to `created_at` or `created_by`, then
  writes a fresh `updated_at` and `updated_by`; and
- permits domain-driven `deleted_at` soft delete and restore changes, which
  still receive the new updater pair.

Missing or invalid actor binding and creator-field tampering raise before SQL is
issued. HTTP's request UoW rolls back the entire request; explicit non-HTTP
transaction owners roll back their own transaction. The hook never inserts a
fallback UUID, creates a User, or logs an identity value.

## HTTP Actor Binding

`AuditedWriteSessionDep` is a composition dependency over the existing
`WriteSessionDep` and `CurrentUser`. It receives the same cached `get_db`
Session used by authentication, binds `CurrentUser.id`, and returns that Session
without adding another commit or rollback owner. Inventory and scheduler write
routes use this dependency; their service methods no longer accept or construct
audit field values.

The business field `SchedulerRun.requested_by` remains separate from audit
metadata. Manual scheduler run/backfill routes still persist the requesting
human UUID so future worker execution can recover the origin. Public request
schemas already reject unknown audit fields and remain unchanged, so no OpenAPI
client generation is expected from this task.

## Non-HTTP Actor Propagation

| Entry point | Actor selected | AuditFields write |
| --- | --- | --- |
| Inventory CLI import | Existing active human or any pre-provisioned System Actor `actor_user_id` | Bind before importing; reject missing or inactive human actor; remove all manual audit assignments. |
| Startup scheduler bootstrap | Default System Actor (`system_actor_key=system`) | Bind before `bootstrap_inventory_jobs()` creates a `SchedulerJob`. |
| Scheduled job scan | Default System Actor (`system_actor_key=system`) | Bind before changing `SchedulerJob.next_run_at` or creating bootstrap-derived job state. |
| Manual run/backfill worker execution | Persisted `SchedulerRun.requested_by` | Add UUID to `ScheduledTaskContext`; bind before any task-owned audit write and before final `SchedulerJob` mutation. |
| Scheduled/recovered run execution | Default System Actor (`system_actor_key=system`) | Resolve once from the durable run context, then use as above. |
| Scheduler alert update | Actor of the run that caused it, or default System Actor for scanner-only alerts | Pass UUID to `_send_alert()` and bind before alert fields modify `SchedulerJob`. |
| Daily report and delivery workers | None | These tables do not inherit `AuditFields`; retain the technical-record contract and do not fabricate an actor. |

Celery still receives only the numeric `run_id`. `execute_run()` reloads the
durable run, resolves `requested_by` or the System Actor UUID, and builds a
`ScheduledTaskContext` containing the UUID rather than a `User` instance.
At-least-once retries recompute that actor from the same durable data, preserving
manual attribution without logging it or placing it in broker payloads.

## Protected System User Boundary

Every System Actor is a database attribution target, not a managed identity:

- authentication and token resolution reject `is_system_actor`, even if its
  active flag is later misconfigured;
- password recovery, reset, and password-recovery HTML content treat it as
  absent/invalid and never send mail;
- user list queries exclude it; direct user reads use non-disclosing not-found
  semantics; and update, delete, self-service update, and password update
  reject it;
- IAM role replacement rejects it before deleting or inserting any assignments;
  initialization never grants it a role; and
- public DTOs never reveal the private marker.

Login and recovery responses preserve the current anti-enumeration messages.
System Actor display emails are provisioning metadata; the protected marker and
unique `system_actor_key` are the runtime identity contract.

## Failure, Rollout, And Observability

Deploy the migration before code that depends on the marker. On application
startup the initializer establishes the actor before audited bootstrap work; a
missing actor later in workers is a fail-closed application error, not an
opportunity to seed from an arbitrary task process.

All actor identities remain absent from structlog context. Existing logging may
retain only the low-cardinality HTTP `actor_kind` and Celery `task_id` /
`task_name`; request error responses continue using the established
`detail + request_id` contract.
