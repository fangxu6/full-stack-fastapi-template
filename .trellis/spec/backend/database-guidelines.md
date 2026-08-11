# Database Guidelines

> SQLModel, schema, and Alembic rules for this repository.

---

## Overview

The backend uses SQLModel + SQLAlchemy on PostgreSQL. Model and schema conventions still largely reflect the upstream template, but this repo now treats them as explicit platform contracts that future business modules must preserve.

---

## Current Reality

### Core entities

- `User` is the main identity and permission subject:
  - [`backend/app/models/user.py`](../../../backend/app/models/user.py)
  - [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- `Item` is still a template-style business entity:
  - [`backend/app/models/item.py`](../../../backend/app/models/item.py)
  - [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)

### Shared constraints

- Primary keys use UUIDs:
  - [`backend/app/models/user.py`](../../../backend/app/models/user.py)
  - [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- `created_at` uses timezone-aware UTC timestamps through `get_datetime_utc`:
  - [`backend/app/models/user.py`](../../../backend/app/models/user.py)
  - [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- Existing `User` and `Item` tables have only the template's `created_at`; they do
  not yet implement the full audit-field contract below.
- Ownership from `Item` to `User` is modeled with `owner_id` and `ondelete="CASCADE"`:
  - [`backend/app/models/item.py`](../../../backend/app/models/item.py)

### API schema families

- User payload families:
  - `UserCreate`, `UserRegister`, `UserUpdate`, `UserUpdateMe`, `UserPublic`, `UsersPublic`, `UpdatePassword`
  - [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- Item payload families:
  - `ItemCreate`, `ItemUpdate`, `ItemPublic`, `ItemsPublic`
  - [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)

---

## Modeling Rules

- Keep SQLModel table classes in `models/*` and transport contracts in `schemas/*`.
- Preserve UUID identifiers on existing tables. New independent entities follow
  the BIGINT identity contract below.
- Use `<resource>_id` for foreign-key fields such as `owner_id`.
- Keep timestamp fields in UTC with timezone-aware storage.
- Public list wrappers should keep the existing `data + count` shape, for example `UsersPublic` and `ItemsPublic`.

### PostgreSQL Chinese Comments

- This is a forward-only requirement: every new table and every new physical
  column, including primary, foreign-key, status, and audit columns, has a
  non-empty Chinese business comment stored as PostgreSQL `COMMENT` metadata.
- `Field(description=...)`, OpenAPI metadata, and Python source comments do
  not substitute for a database comment. Define table comments in
  `__table_args__` (`{"comment": "..."}` is the final tuple item when the
  table also has constraints or indexes). Define simple column comments with
  `sa_column_kwargs={"comment": "..."}` and add `comment` directly to an
  existing `sa_column=Column(...)` definition.
- A new table inheriting `AuditFields` requires comments for all inherited
  physical audit columns. Own those standard comments in `AuditFields`, not in
  each child model.
- Do not retroactively alter existing tables or rewrite historical revisions
  solely for comments. A historical backfill needs a separate task and
  migration.

---

## Scenario: Extensible Persisted Business States

### 1. Scope / Trigger

Apply this forward-only contract when adding a persisted business field that
expresses a lifecycle, operational mode, eligibility, or other finite state
whose values could reasonably grow beyond two choices. Do not introduce a
boolean merely because the first release currently has an enabled/disabled or
yes/no presentation.

When that persisted state also participates in a DDD workflow with events,
terminal outcomes, retries, leases, recovery, concurrency, permissions, or
cross-entity effects, read and apply the [State Transition Design
Guidelines](./state-transition-guidelines.md). That rule defines the design
matrix; this section remains the authority for enum persistence, migrations,
comments, and public schema contracts.

This does not require converting existing boolean columns. A conversion needs a
separate compatibility and migration task. A boolean remains appropriate for a
true binary fact or a technical switch whose two values are exhaustive and do
not represent a business state. An open-ended or administrator-managed
classification is not an enum either; model it as a referenced dictionary or
domain table.

### 2. Signatures

Use one `StrEnum` as the model, schema, and persisted-value contract, backed by
a named PostgreSQL enum type. The type name uses the owning module namespace
and the field name, for example `approval_state`.

```python
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class ApprovalState(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    SUSPENDED = "SUSPENDED"


class Approval(SQLModel, table=True):
    state: ApprovalState = Field(
        default=ApprovalState.DRAFT,
        sa_type=SAEnum(ApprovalState, name="approval_state"),
        sa_column_kwargs={"comment": "审批状态"},
    )
```

The creating Alembic revision declares the matching named type with
`postgresql.ENUM(..., name="approval_state", create_type=False)`, creates it
with `checkfirst=True` before the table, and drops it only after all dependent
tables are dropped during downgrade.

### 3. Contracts

- Enum members are stable serialized identifiers. Use explicit values and an
  explicit model default when the business state has a default; do not rely on
  enum declaration order or a boolean's `False` value to imply state.
- The SQLModel field and every create, update, filter, and public response
  schema use the same `StrEnum`, so OpenAPI exposes the complete allowed set
  instead of a lossy boolean.
- Every new enum column remains subject to the PostgreSQL Chinese-comment rule.
- Add a new enum member through a forward Alembic migration that updates the
  named PostgreSQL type before application code can persist the value. Do not
  silently rename, delete, or reorder deployed members; those operations need
  an explicit compatibility, data, and rollback design.
- A field that needs user-defined, tenant-defined, or otherwise unbounded
  values uses a foreign-keyed reference table, not a PostgreSQL enum.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| New persisted business state may later need a third value | Define a named `StrEnum` and PostgreSQL enum; do not use `bool`. |
| New field is an exhaustive binary fact or technical switch | `bool` is allowed; record why no additional business state exists. |
| Client supplies a value outside the public enum | Reject with the existing 422 validation contract. |
| New enum value exists only in Python source | Block release until a forward Alembic migration adds the PostgreSQL value. |
| Deployed enum member must be renamed, removed, or reordered | Create a separate compatibility/migration plan; do not mutate the original type in place. |
| Existing boolean is discovered during unrelated work | Preserve it unless its task explicitly includes a reviewed conversion. |

### 5. Good / Base / Bad Cases

- Good: a new approval workflow begins with `DRAFT` and `APPROVED` but stores
  `ApprovalState`, leaving `SUSPENDED` and later states as additive enum
  members rather than forcing a boolean-to-state migration.
- Base: a persisted checksum result is intrinsically `true` or `false` and has
  no additional lifecycle meaning, so a boolean remains appropriate.
- Bad: a new entity stores `is_active: bool` even though operations can later
  require `SUSPENDED`, `ARCHIVED`, or `PENDING_REVIEW` behavior.

### 6. Tests Required

- Model/migration test: assert the field uses the named enum type, the
  migration creates the type before its dependent column, and downgrade drops
  dependents before the type.
- API test: assert accepted enum values round-trip and an unknown value returns
  the standard 422 validation response.
- Evolution test: when adding a member, upgrade an isolated predecessor
  database and assert the new value is accepted without changing existing
  values.
- Cross-layer test: when the field is public, regenerate and type-check the
  frontend client so enum consumers receive the expanded allowed set.

### 7. Wrong vs Correct

#### Wrong

```python
class Approval(SQLModel, table=True):
    is_active: bool = Field(default=False)
```

`False` cannot distinguish a draft, suspended, archived, or rejected approval,
so adding any of those states later requires a cross-layer data conversion.

#### Correct

```python
class Approval(SQLModel, table=True):
    state: ApprovalState = Field(
        default=ApprovalState.DRAFT,
        sa_type=SAEnum(ApprovalState, name="approval_state"),
    )
```

The named enum preserves the complete business state, validates its public
contract, and permits future additive states through an explicit migration.

---

## Scenario: New Entity Primary Keys

### 1. Scope / Trigger

Apply this contract when a new durable business table, document, ledger, or
independently addressable document line is introduced. It is forward-only and
does not migrate existing UUID primary keys.

### 2. Signatures

```sql
id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY
```

- PostgreSQL `BIGINT` is signed and positive identity values end at `2^63 - 1`.
  Do not use `BIGINT(20)`, unsigned ranges, `serial`, or `bigserial`.
- A new BIGINT entity can reference an existing UUID table: its `user_id`,
  `created_by`, or other foreign key remains UUID while its own `id` is BIGINT.

### 3. Contracts

- Each normal table has an independent sequence. IDs are immutable, never
  reused, and may have gaps.
- Pure association tables with no independent lifecycle may use their foreign
  keys as a composite primary key. Independently referenced or audited lines
  need their own BIGINT identity plus a domain unique constraint such as
  `(document_id, line_no)`.
- Business identifiers remain separate domain fields. They never replace a
  technical primary key or authorize access to it.
- UUID primary keys require a design rationale: cross-system/offline merge,
  opaque external identity, or a one-to-one table sharing an existing UUID
  parent's primary key.
- Create and update DTOs use `extra="forbid"` and do not declare `id`; a
  client-supplied ID is a 422 validation failure. Only controlled migrations
  use `OVERRIDING SYSTEM VALUE` and then realign the identity sequence.
- Each module must document whether its resource access domain is
  internal-global, owner-scoped, unit-scoped, or administrator-scoped. Service
  authorization returns 403 for an existing inaccessible row and 404 for a
  missing or deleted row.
- Public BIGINT IDs are JSON numbers. At `MAX(id) >= 2^53 - 1`, emit an
  operational alert only. Precision loss above that boundary is an explicitly
  accepted risk.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| New independent entity | BIGINT identity primary key in model and migration |
| UUID parent/audit reference | UUID foreign-key column matching the target type |
| Client supplies `id` on create/update | 422 through the shared error contract |
| Existing row outside access domain | 403 through the shared error contract |
| Missing or deleted row | 404 through the shared error contract |
| `MAX(id) >= 2^53 - 1` | Operational alert; no automatic write block or API conversion |

### 5. Good / Base / Bad Cases

- Good: a new `production_order` owns a BIGINT identity while `created_by`
  remains a UUID foreign key to `user.id`.
- Base: a UUID-keyed `user_preferences` one-to-one extension uses `user_id` as
  both its UUID primary key and foreign key.
- Bad: a new independent order switches to UUID solely because it references
  `user.id`, or an API silently ignores a caller-provided identity value.

### 6. Tests Required

- Migration/model test: assert the primary-key type and generated-always
  identity, target-matching foreign-key types, and any line-number or
  association-table constraint.
- API test: database assigns the ID; input `id` receives 422; the module's
  declared authorization returns 403/404 correctly.
- Cross-layer test: public numeric IDs compile through generated OpenAPI client
  consumers whenever a new endpoint is introduced.
- Operations check: document or implement a per-table `MAX(id)` alert at
  `9007199254740991`.

### 7. Wrong vs Correct

#### Wrong

```python
class ProductionOrder(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_by: uuid.UUID = Field(foreign_key="user.id")
```

The new independent entity has no UUID requirement; the existing UUID foreign
key does not determine its own primary-key type.

#### Correct

```python
import uuid

from sqlalchemy import BigInteger, Column, Identity
from sqlmodel import Field, SQLModel


class ProductionOrder(SQLModel, table=True):
    id: int | None = Field(
        default=None,
        sa_column=Column(
            BigInteger,
            Identity(always=True),
            primary_key=True,
        ),
    )
    created_by: uuid.UUID = Field(foreign_key="user.id")
```

The production migration must explicitly emit the PostgreSQL BIGINT generated
always identity column and match the model metadata.

---

## Scenario: Module Database Object Namespace

### 1. Scope / Trigger

When a bounded business module introduces one or more durable database objects,
give that module a stable lowercase domain prefix. Apply it to new tables,
explicitly named indexes, constraints, sequences, and Alembic revision
descriptions. This prevents unrelated features from creating ambiguous names
such as `run`, `log`, `state`, or `record`, which made later inspection and
operations harder in the CRM inbound/outbound work.

This is a forward-only convention. Do not rename existing production tables
solely to comply; a rename requires its own compatibility, migration, and
rollback task.

### 2. Signatures

Use a stable module identifier as the domain namespace:

| Object kind | Required form | Example |
| --- | --- | --- |
| Table | `<domain>_<noun>` | `reporting_run`, `reporting_export` |
| Index | `ix_<domain>_<table-noun>_<columns>` | `ix_reporting_run_request_id` |
| Unique constraint | `uq_<domain>_<table-noun>_<columns>` | `uq_reporting_export_run_sequence` |
| Check constraint | `ck_<domain>_<table-noun>_<rule>` | `ck_reporting_run_exports` |
| Foreign key | `fk_<domain>_<table-noun>_<target>` | `fk_reporting_export_run` |
| Sequence | `seq_<domain>_<noun>` | `seq_reporting_run_number` |
| Alembic description | `create_<domain>_<objects>` | `create_reporting_audit_tables` |

The conventional object-kind prefix (`ix_`, `uq_`, `fk_`, and so on) comes
first; the domain prefix must immediately follow it. For a module with domain
`reporting`, every new persistent object is therefore discoverable with
`reporting_` in its
name.

### 3. Contracts

- Choose the domain prefix in the task `prd.md`/`design.md` before generating
  the first migration. It must describe the bounded capability, not a temporary
  screen or implementation detail.
- Use the same prefix across all child tasks of one initiative. A sidecar,
  frontend, or evaluation task that later adds persistence inherits the parent
  module prefix instead of inventing another namespace.
- Explicitly name multi-column indexes and constraints. Do not rely on a
  generated database name that drops the domain context.
- Keep existing shared/platform tables in their existing namespace. A new
  cross-module table needs an explicit owner and prefix decision in its design.
- Models, schemas, Python classes, and API routes do not need to start with the
  database prefix; this rule owns persisted database object names only.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| New table lacks the approved domain prefix | Stop migration review; rename it before applying the migration. |
| Explicit index or constraint omits the domain prefix | Give it an explicit compliant name before merge. |
| Existing production table lacks a prefix | Preserve it; create a separate compatibility task if a rename is truly required. |
| Child task proposes a different prefix for the same module | Reject the divergence and use the parent module prefix. |
| New cross-module/shared table has no clear owner | Resolve owner and namespace in the design before migration generation. |

### 5. Good / Base / Bad Cases

- Good: the reporting module creates `reporting_run`, `reporting_export`,
  `ix_reporting_run_request_id`, and `uq_reporting_export_run_sequence`;
  operations can list the entire module family by searching `reporting_`.
- Base: an existing `inventory_document` remains unchanged while a new reporting
  audit table references it or `user`; the new object still uses `reporting_`.
- Bad: a new CRM or reporting feature adds generic `run`, `events`, or `log_entries`
  tables and unnamed constraints. Operators cannot reliably group, audit, or
  clean up the feature's persistence footprint.

### 6. Tests Required

- Migration test: inspect the migrated schema/metadata and assert each new
  table has the approved `<domain>_` prefix.
- Schema test: assert explicitly named indexes, unique/check/foreign-key
  constraints, and sequences use the corresponding kind-plus-domain form.
- Upgrade/downgrade test: run only against an isolated `_test` or `_pytest`
  database and verify no existing unrelated table was renamed.
- Review test: when a public schema/API change accompanies the migration,
  perform the existing generated-client impact review separately; database
  naming does not exempt cross-layer contract checks.

### 7. Wrong vs Correct

#### Wrong

```python
class Run(SQLModel, table=True):
    __tablename__ = "run"

    request_id: str


Index("request_id_index", Run.request_id)
```

The table and index do not identify their owning module, so operational schema
inspection cannot distinguish them from other feature runs.

#### Correct

```python
class ReportingRun(SQLModel, table=True):
    __tablename__ = "reporting_run"

    request_id: str


Index("ix_reporting_run_request_id", ReportingRun.request_id)
```

The model name remains idiomatic Python while every persisted object carries a
stable reporting namespace.

---

## Audit Field Contract

### 1. Scope / Trigger

Every new durable business table must include the audit-field contract below. This
applies to user-maintained master data, documents, document lines, inventory
ledger entries, controlled-import batches, and source rows. It does not
retroactively change the platform `User` or template `Item` tables; changing
those requires a separately reviewed migration.

Use the term **audit fields** in task `design.md` files instead of repeating the
five columns in every table definition. A design must still state any exception
and the actor source for non-HTTP writes.

### 2. Signatures

| Field | PostgreSQL type and constraint | Meaning |
|---|---|---|
| `created_at` | `TIMESTAMPTZ NOT NULL` | UTC time at first persistence; immutable. |
| `created_by` | `UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT` | Authenticated user or explicitly supplied command actor that created the row; immutable. |
| `updated_at` | `TIMESTAMPTZ NOT NULL` | UTC time of the most recent persisted mutation. Equal to `created_at` on insert. |
| `updated_by` | `UUID NOT NULL REFERENCES "user"(id) ON DELETE RESTRICT` | Authenticated user or explicitly supplied command actor that made the most recent mutation. Equal to `created_by` on insert. |
| `deleted_at` | `TIMESTAMPTZ NULL` | Soft-delete time in UTC. `NULL` rows are active; only an explicit delete or restore service operation may change it. |

SQLModel fields use `uuid.UUID`, `datetime`, `DateTime(timezone=True)`, and
`get_datetime_utc`. New table models may obtain the fields from a shared audit
mixin, but the Alembic revision must emit the four concrete columns and both
foreign keys for every table in scope.

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel

from app.models.base import get_datetime_utc


class AuditFields(SQLModel):
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    created_by: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="RESTRICT"
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
        nullable=False,
    )
    updated_by: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="RESTRICT"
    )
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        nullable=True,
    )
```

The audit listener owns all four actor/timestamp values and `deleted_at` stays
`None` on creation. Ordinary updates change only `updated_at` and `updated_by`.
`created_at`, `created_by`, and `deleted_at` are never accepted from public
create or update payloads.

### 3. Contracts

- HTTP mutations bind the authenticated user to the existing write `Session`
  through `AuditedWriteSessionDep`. Services and repositories must not accept,
  infer, or assign audit actor fields themselves.
- User-initiated commands and importers require an `actor_user_id: UUID`, bind
  it to their owned session before the first auditable flush, and clear it when
  the session scope ends. Automated scheduler paths may instead use the one
  protected System Actor. They must not write `NULL`, a sentinel UUID, or an
  ad hoc fabricated user.
- Soft deletion is an update: set `deleted_at` to the current UTC time, retain
  the original creator, and set `updated_at` / `updated_by` to the deletion
  actor. Restore sets `deleted_at=NULL` and updates the same updater pair.
- API response DTOs expose audit fields only on detail or history endpoints
  where they are needed for traceability. Create and update DTOs never accept
  them from clients.
- `ON DELETE RESTRICT` preserves audit history. A user referenced by any audit
  field cannot be physically deleted; deactivate the user instead.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| HTTP mutation has no authenticated actor | Reject through the existing authentication flow; do not persist a row. |
| User-initiated command lacks `actor_user_id`, or any audited flush has no binding | Reject before the business row persists with a validation or `AuditActorError`; no partial commit. |
| Supplied actor does not exist | Reject with the repository's not-found or validation error; do not persist a row. |
| Client sends a creator or updater field in a public payload | Ignore no values silently: reject the payload schema as unsupported. |
| Client sends `deleted_at` in a create or ordinary update payload | Reject the payload schema as unsupported; use the explicit delete or restore operation. |
| Update tries to alter a creator field | Reject as a validation or domain error; preserve the original values. |
| User deletion is blocked by an audit reference | Surface a semantic conflict; require deactivation rather than physical deletion. |

### 5. Good / Base / Bad Cases

- Good: a receipt is created through a bound request session. The listener sets
  both creator and updater IDs to that user's UUID at the same UTC instant.
- Base: editing the receipt changes only the updater pair; the creator pair
  remains unchanged.
- Bad: an Excel importer writes rows with `created_by = NULL` because it runs
  outside HTTP, or a worker invents its own actor. The importer binds the
  operator UUID; an automated scheduler resolves the System Actor.

### 6. Tests Required

- Insert test: assert the listener sets all four actor/timestamp fields, the
  two creator/updater pairs are equal on creation, and `deleted_at` is `NULL`.
- Update test: assert only the updater pair changes, while creator fields remain
  unchanged.
- Soft-delete/restore test: assert delete sets a UTC `deleted_at` value and
  changes the updater pair; restore sets it back to `NULL` without changing
  creator fields.
- Authorization/command test: assert unauthenticated mutation, invalid actor,
  and an audited flush without a binding fail before inserting business rows.
- Referential-integrity test: assert physical deletion of a referenced user is
  rejected, while user deactivation preserves historical rows.
- Migration test: assert every new in-scope table contains the five audit
  columns, UTC timestamp types, non-null constraints, and two foreign keys to
  `user.id`.

### 7. Wrong vs Correct

#### Wrong

```python
document = InventoryDocument()
document.created_by = current_user.id
```

This lets a caller forge audit history and leaves command-driven writes without
an accountable actor.

#### Correct

```python
bind_audit_actor(session=session, actor_id=current_user.id)
document = InventoryDocument(...)
session.add(document)
```

For a later mutation, bind the actor to the transaction and update only
business fields. The listener changes `updated_at` and `updated_by` in the
same flush.

---

## Scenario: Explicit Audit Actor and System Actor

### 1. Scope / Trigger

- Trigger: a write can persist one of `ProcessingUnit`, `ReceivingUnit`,
  `InventoryDocument`, `InventoryDocumentLine`, `InventoryImportBatch`,
  `LegacyImportRow`, `InventoryLedgerEntry`, or `SchedulerJob`.
- The contract applies to HTTP routes, the inventory importer, initialization,
  and scheduler runtime paths. `User`, `Item`, `SchedulerRun`, daily reports,
  and deliveries remain outside this audit-listener scope.

### 2. Signatures

```python
bind_audit_actor(*, session: Session, actor_id: uuid.UUID) -> None
clear_audit_actor(*, session: Session) -> None
ensure_system_actor(*, session: Session) -> User
require_system_actor(*, session: Session) -> uuid.UUID
AuditedWriteSessionDep = Annotated[Session, Depends(...)]
```

- The session key is private to `app.core.audit`; actor propagation uses only
  `Session.info`, never a context variable, request object, detached `User`,
  log context, or broker payload.
- `User.is_system_actor` and private `system_actor_key` identify protected
  non-human accounts. A check constraint requires a key exactly for a System
  Actor, and a PostgreSQL partial unique index makes each key unique. The
  default key `system` has email `system@example.com`, an unusable random
  password, `is_active=False`, and zero IAM roles; provisioning may create
  additional keys with explicit display emails.

### 3. Contracts

- The SQLAlchemy `before_flush` listener stamps new audited rows and refreshes
  only `updated_at` / `updated_by` for material audited updates. It rejects a
  missing, nonexistent, or pending-deleted actor and creator-field tampering.
- `AuditedWriteSessionDep` composes the request Unit of Work with
  `CurrentUser`; it must reuse the same session and must not add a commit
  owner. Non-HTTP owners bind and clear around their own transaction scope.
- `init_db()` creates the System Actor before scheduler bootstrap. Scheduler
  scans, bootstrap, alert throttling, and scheduled runs bind it. Manual runs
  preserve the durable human `SchedulerRun.requested_by` as their actor across
  worker retry/reclaim.
- `requested_by` is business attribution for `SchedulerRun`, not an audit
  field. Scheduled runs retain `requested_by=NULL`; it never acquires the
  System Actor UUID solely for audit purposes.
- Every System Actor is private infrastructure: it cannot log in, receive or
  use a password reset, appear in user list/detail output, be updated/deleted,
  or receive roles. Public schemas and OpenAPI never expose `is_system_actor`
  or `system_actor_key`.
- The marker/key migration is forward-only once a System Actor reference exists
  in any of the eight audited tables. Downgrade must reject that state rather
  than erasing audit semantics.

### 4. Validation and Error Matrix

| Condition | Required behavior |
| --- | --- |
| Audited insert/update without a valid bound UUID | `AuditActorError` before flush/commit; no persisted business mutation. |
| Caller changes `created_at` or `created_by` after insert | `AuditActorError`; creator fields stay unchanged. |
| HTTP inventory or scheduler write | Bind `CurrentUser.id` through `AuditedWriteSessionDep` in the request UoW. |
| Importer write | Require and bind an active human or pre-provisioned System Actor `actor_user_id`; reject a missing or inactive human actor. |
| Scheduled scan, bootstrap, or alert-only mutation | Resolve and bind the default System Actor key `system`. |
| Manual scheduler execution finalizes an audited job | Bind the run's persisted `requested_by`; do not substitute System Actor. |
| System Actor management/auth request | Preserve the existing non-disclosing public failure shape; no mutable side effect. |
| Downgrade after System Actor audit reference | Raise and require a forward fix or database backup restore. |

### 5. Good / Base / Bad Cases

- Good: an authenticated inventory create uses one request session. The listener
  persists both actor pairs as the current human without service assignments.
- Base: scheduler scanning creates a `SchedulerRun` with `requested_by=NULL`
  while the listener attributes its `SchedulerJob` mutation to System Actor.
- Bad: a Celery message carries an actor UUID or a worker uses a detached
  `User`. Reload the persisted run and resolve the actor into its local session.

### 6. Tests Required

- Cover insert, update, soft-delete/restore, missing/invalid/deleted actor, and
  creator tampering for all eight audited models.
- Cover default and custom System Actor provisioning, key uniqueness, public/auth
  protection, role mutation rejection, and migration downgrade before/after an
  audit reference.
- Cover request-session identity reuse, importer binding and rollback, manual
  scheduler retry/reclaim actor preservation, and default System Actor scheduler
  paths.
- Run destructive backend tests and isolated API validation with
  `POSTGRES_DB=aiadmin_test`; use a fresh session asserting inventory and
  scheduler persistence, plus System Actor list/detail/login/recovery/role
  protection.

### 7. Wrong vs Correct

#### Wrong

```python
run_task.delay(run_id, current_user.id)
job.updated_by = current_user.id
```

The broker payload leaks attribution state and manual field assignment bypasses
the authoritative listener.

#### Correct

```python
actor_id = run.requested_by or require_system_actor(session=session)
bind_audit_actor(session=session, actor_id=actor_id)
job.run_failure_alerted_at = None
session.commit()
```

The worker passes only the durable run ID, reloads its actor into the local
session, and lets the listener own the audit fields.

---

## Scenario: Semantic Change Audit Events

### 1. Scope / Trigger

Apply this when a high-value mutation needs durable, queryable evidence of
**what business change occurred**, in addition to entity `created_by` /
`updated_by` fields and operational logs. The first owner is IAM role and
user-role mutation; another module may reuse the storage only after it defines
its own action codes and allowed summary fields.

### 2. Signatures

```python
class AuditEvent(SQLModel, table=True):
    id: int | None  # BIGINT GENERATED ALWAYS AS IDENTITY
    occurred_at: datetime  # TIMESTAMPTZ NOT NULL DEFAULT now()
    actor_user_id: uuid.UUID | None
    request_id: str | None
    action: str  # VARCHAR(128), for example iam.role.created
    resource_type: str  # VARCHAR(64), for example iam_role
    resource_id: str  # VARCHAR(128), UUID and BIGINT encoded as text
    changes: dict[str, object]  # JSONB object

def append_audit_event(*, session: Session, actor_user_id: uuid.UUID | None,
                       request_id: str | None, action: str,
                       resource_type: str, resource_id: str,
                       changes: dict[str, object]) -> None: ...

def cleanup_expired_events(*, session: Session,
                           now: datetime | None = None) -> int: ...
```

- Table: `audit_event`, with `CHECK (jsonb_typeof(changes) = 'object')` and
  indexes on `occurred_at DESC`, `(resource_type, resource_id, occurred_at
  DESC)`, and `(actor_user_id, occurred_at DESC)`.
- The direct Celery Beat task is `audit.cleanup_events`; it runs daily and is
  not a `SchedulerJob`.

### 3. Contracts

- `AuditEvent` is not an entity audit-field mixin. It has no foreign keys,
  `updated_at`, soft delete, update endpoint, PostgreSQL enum, or reader API.
  The nullable actor UUID intentionally preserves history if a user is deleted.
- Action codes and resource types are stable, lowercase, dot/noun names owned
  by the source module. The source module validates its action/resource/summary
  allowlist before invoking the generic writer. The writer accepts only an
  object summary and never receives a request body or client-supplied actor.
- HTTP routes pass `CurrentUser.id` and middleware-owned
  `request.state.request_id` into their service. The service reads any
  allowlisted before-state, mutates its existing entities, and adds exactly one
  event to the same `WriteSessionDep` session after successful validation.
  `WriteSessionDep` commits or rolls back the business change and event
  together; the writer must never commit, catch, or independently persist it.
- `changes` is data-minimized: identifiers, booleans, and approved field names
  only. Do not store email, names, descriptions, passwords, tokens, raw request
  or response bodies, or unrestricted old/new rows.
- Retention deletes only `occurred_at < now - 365 days`. No reader/export,
  database trigger, privilege model, legal hold, external sink, or
  tamper-resistance claim exists until a separately approved task defines it.
- The creating migration supplies Chinese comments for the table and every
  column. Downgrade must refuse while rows exist; an application rollback leaves
  the table and evidence intact.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| IAM mutation succeeds and its request commits | Persist exactly one matching event in the same commit. |
| IAM validation, authorization, or persistence fails | Roll back the business mutation and write no event. |
| Action/resource/summary is outside its module allowlist | Raise before final commit; do not serialize arbitrary data. |
| Event timestamp is exactly 365 days old | Retain it; only strictly older events are deleted. |
| Schema downgrade finds an event row | Raise and preserve the table; require an explicit evidence decision. |

### 5. Good / Base / Bad Cases

- Good: `iam.role.permissions_replaced` records only permission-code lists
  before/after against `iam_role/<id>` and the current actor/request ID.
- Base: a non-HTTP future writer records `request_id=NULL` with a resolved
  actor, following its own action-summary allowlist.
- Bad: serializing `role_in.model_dump()` or an ORM row into `changes`, adding
  an event after a route commits, or modeling the daily cleanup as a user-facing
  scheduler job.

### 6. Tests Required

- API test every initial action code, actor ID, request ID, resource ID, and
  allowed summary; include a mixed state/non-state PATCH without free-text
  values in its event.
- Failure test: an IAM mutation that returns an existing domain error leaves
  the event count unchanged.
- Retention test: delete a 366-day-old row and retain a row exactly 365 days
  old.
- Migration test: upgrade an isolated `_test`/`_pytest` database; inspect the
  table/column comments, three indexes, and JSONB-object check. Verify nonempty
  downgrade refusal, then empty-table downgrade and re-upgrade.
- Celery test: assert `audit.cleanup_events` is registered and scheduled daily.

### 7. Wrong vs Correct

#### Wrong

```python
append_audit_event(
    session=session,
    actor_user_id=current_user.id,
    request_id=request.state.request_id,
    action="iam.role.updated",
    resource_type="iam_role",
    resource_id=str(role.id),
    changes=role_in.model_dump(),
)
session.commit()
```

This leaks arbitrary input and can persist evidence separately from the role
mutation.

#### Correct

```python
append_audit_event(
    session=session,
    actor_user_id=actor_user_id,
    request_id=request_id,
    action="iam.role.updated",
    resource_type="iam_role",
    resource_id=str(role.id),
    changes={"changed_fields": ["name"]},
)
```

The owning service has already validated the static summary; the shared request
Unit of Work owns the one final commit.

---

## Scenario: Serializing IAM Role Semantic Mutations

### 1. Scope / Trigger

Apply this when an existing IAM role is mutated and the service needs its
current row or permission links to build semantic audit evidence. Concurrent
requests must not both read the same pre-mutation state and then interleave a
delete-and-replace of that role's permission links. This applies to role PATCH,
permission replacement, and deletion; it does not make ordinary role reads
locking reads.

### 2. Signatures

```python
def get_role_by_id(
    *, session: Session, role_id: int, lock: bool = False
) -> IamRole | None: ...

role = repository.get_role_by_id(session=session, role_id=role_id, lock=True)
```

With `lock=True`, the repository executes the PostgreSQL equivalent of:

```sql
SELECT * FROM iam_role WHERE id = :role_id FOR UPDATE;
```

The transaction keeps this row lock until the request Unit of Work commits or
rolls back. After acquiring it, the service may read permission codes, validate
the command, write the role/links, and append its audit event in that same
transaction.

### 3. Contracts

- `get_role_by_id(..., lock=False)` remains the default for read-only callers;
  it uses the ordinary identity lookup and must not take a row lock.
- Every mutation of an existing IAM role requests `lock=True` before inspecting
  role state, permission links, assignment/deletion eligibility, timestamps,
  or audit `before` values. Do not acquire the lock after reading a snapshot.
- A second mutation of the same role waits for the first request to commit or
  roll back, then reads the now-current committed state. Its audit `before`
  value describes that transition, and its permission replacement becomes the
  complete final set rather than a merged residual set.
- `PATCH /api/v1/iam/roles/{role_id}` computes supplied fields with
  `model_dump(exclude_unset=True)` and updates only values that differ from the
  locked row. An empty body or an all-equal body raises `IamValidationError`
  with the shared 422 `detail` and `request_id` response contract.
- A no-op PATCH does not update `updated_at`, flush, append an `AuditEvent`, or
  cause a business mutation. A PATCH with at least one real difference retains
  the normal response and writes exactly one allowlisted semantic event whose
  `changed_fields` contains only values from the actual-change dictionary.
- Keep this operation database-scoped. A Python process lock cannot coordinate
  separate Uvicorn workers, background processes, or hosts, whereas PostgreSQL
  row locks coordinate all transactions that share the database.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Mutation targets an existing role | Acquire `FOR UPDATE` before reading evidence or mutating role-owned links. |
| Concurrent permission replacement targets the same role | Second transaction waits, reads the first committed set as `before`, and writes only its requested final set. |
| Role does not exist after the locked lookup | Return the existing not-found error; write no audit event. |
| PATCH body has no supplied fields | Return shared HTTP 422; preserve role and event count. |
| Every supplied PATCH value equals the stored value | Return shared HTTP 422; preserve `updated_at` and event count. |
| PATCH contains one or more changed values | Update those values, refresh the result, and append exactly one corresponding semantic event. |

### 5. Good / Base / Bad Cases

- Good: request A replaces role permissions with `["inventory.ledger.read"]`;
  request B then acquires the same row lock, records that set as `before`, and
  replaces it with `["inventory.balances.read"]`. The durable final set is
  exactly B's list.
- Base: `PATCH {"is_active": false}` on an active custom role locks the row,
  changes the boolean, and records exact `before` / `after` values in one
  `iam.role.deactivated` event.
- Bad: two sessions read permission links without locking the role, both delete
  links, and both add their desired links. PostgreSQL then retains a mixed set
  while the second event claims an obsolete `before` snapshot.

### 6. Tests Required

- Two-session service regression: begin a replacement in one session, prove a
  second same-role replacement cannot complete until the first commits, then
  assert its event `before` list is the first request's exact `after` list and
  the final links equal only the second requested set.
- API regressions: empty PATCH and same-value PATCH each return 422 with
  `detail`, `request_id`, and `X-Request-ID`; assert unchanged `updated_at` and
  audit-event count.
- Existing real-change PATCH regression: assert the response shape and exactly
  one event, including precise boolean transition values for `is_active`. A
  mixed PATCH with an unchanged `is_active` and a changed name must list only
  `name` in `changed_fields`.
- Focused IAM/audit suite and backend lint gate must run against an isolated
  database before commit.

### 7. Wrong vs Correct

#### Wrong

```python
role = repository.get_role_by_id(session=session, role_id=role_id)
before = repository.get_role_permission_codes(session=session, role_id=role_id)
session.exec(delete(IamRolePermission).where(IamRolePermission.role_id == role_id))
```

The ordinary read permits another transaction to observe and rewrite the same
links between the snapshot and replacement, so neither the final set nor the
audit `before` value is reliable.

#### Correct

```python
role = repository.get_role_by_id(session=session, role_id=role_id, lock=True)
before = repository.get_role_permission_codes(session=session, role_id=role_id)
# Validate, replace links, and append the event before this request commits.
```

The locked role serializes same-role semantic writes across all database
clients. It provides the ordering needed for correct audit evidence without
serializing unrelated roles or relying on per-process memory.

---

## Query and Mutation Patterns

- Compose reads with `select(...)`, `where(...)`, `order_by(...)`, `offset(...)`, and `limit(...)`.
- Use `model_validate(...)` to turn ORM objects into public payloads:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Prefer `sqlmodel_update(...)` or `model_dump(exclude_unset=True)` update flows rather than ad hoc patching:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/crud/user.py`](../../../backend/app/crud/user.py)
- Keep ownership and permission filtering in service orchestration. CRUD helpers should stay database-focused and not become hidden authorization layers.
- In HTTP mutation flows, routes, services, and CRUD helpers may `add`, `flush`, and `refresh`, but only the request write dependency may commit or roll back.

---

## Scenario: HTTP Request Unit Of Work

### 1. Scope / Trigger

Apply this to every FastAPI HTTP route that needs a database session. Write
requests own one primary-database transaction shared by authentication,
permission, route, and service dependencies. A selected eventually-consistent
query may use the dedicated read dependency; authentication, RBAC, and any
strongly-consistent or mixed read remain on the primary dependency.

### 2. Signatures

```python
SessionDep = Annotated[Session, Depends(get_db, scope="function")]


def get_read_db() -> Generator[Session]:
    with Session(read_engine) as session:
        yield session


ReadSessionDep = Annotated[Session, Depends(get_read_db, scope="function")]


def get_write_db(
    session: Annotated[Session, Depends(get_db, scope="function")],
) -> Generator[Session]:
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise


WriteSessionDep = Annotated[Session, Depends(get_write_db, scope="function")]
```

`POSTGRES_READ_REPLICA_SERVER: str | None` is optional. `write_engine` always
uses `SQLALCHEMY_DATABASE_URI`; `read_engine` is the same object when the
replica host is unset, otherwise it uses a URI with that host and the primary
port, database, username, and password. Keep `engine = write_engine` for
existing imports. `get_db()` remains the primary request-session factory and
closes the session. `SessionDep` and `WriteSessionDep` use the same callable
and `scope="function"`, so FastAPI reuses one primary `Session` and finalizes
it before response sending.

### 3. Contracts

- Every HTTP write handler declares `WriteSessionDep`, including a write-method
  endpoint that currently only authenticates or reads.
- `SessionDep` remains the dependency for authentication, RBAC, and primary
  reads that require read-after-write consistency. It must use the same
  function scope as `WriteSessionDep`.
- `ReadSessionDep` is only for an explicitly allowlisted, pure business query
  that accepts replication delay. It opens and closes a function-scoped
  `Session`; it does not explicitly commit, roll back, or drain cache
  invalidations.
- An allowlisted route may use `ReadSessionDep` for its business query while
  its `CurrentUser` and `permission_required(...)` sub-dependencies still use
  the primary `SessionDep`. The two sessions are deliberately distinct.
- With no replica host, `read_engine is write_engine` and no second pool is
  created. With a configured replica host, a connection failure stays visible
  through the normal database error path; never retry it against the primary.
- A replica-backed query is eventually consistent. Do not use it for a
  write-following read, a correction-status query, a user/permission lookup,
  or a flow that mixes reads and writes.
- HTTP services, CRUD helpers, and route handlers do not call
  `session.commit()` or `session.rollback()`. They flush to obtain identities
  or translate expected integrity errors before the response is built.
- A successful request commits exactly once at `get_write_db`; any exception
  rolls back the whole request and preserves the original exception/error
  contract.
- Workers, startup initialization, importers, CLI commands, and direct service
  callers are not HTTP requests. Their caller explicitly commits or rolls back
  a short transaction after the operation.
- Do not call SMTP, an HTTP dependency, or a broker while the request database
  transaction is open. Existing HTTP mail paths use `BackgroundTasks` after
  the function-scoped commit. Durable retry and delivery state remain the
  responsibility of the generic email outbox capability.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| HTTP write succeeds | One final commit occurs before the shared session closes. |
| Endpoint, dependency, or service raises | The write dependency rolls back before close; no partial business, audit, or outbox rows persist. |
| Authentication/RBAC and endpoint both need a session | They observe the same cached function-scoped `Session`, not a second request session. |
| Replica host is unset | `ReadSessionDep` uses the primary engine object and does not create a second connection pool. |
| Replica host is configured and the read connection fails | Return the existing database failure; do not fall back to a successful primary read. |
| Allowlisted read also authenticates or checks permission | Auth/RBAC uses primary `SessionDep`; the business query uses the separate `ReadSessionDep`. |
| Query needs write-following visibility or writes | Use `SessionDep` or `WriteSessionDep`, never `ReadSessionDep`. |
| Expected unique/integrity conflict | Flush and convert it to the existing domain error before final commit; the dependency performs the rollback. |
| Direct test setup calls an HTTP route or worker that opens another session | Commit setup data first. After an expected direct-service exception, roll back before asserting durable state. |
| Direct setup retains a row lock and calls a second-session worker | Commit before the worker call so it can read or update the same row without blocking. |

### 5. Good / Base / Bad Cases

- Good: a route creates a user, role links, and an item through services that
  flush, then `WriteSessionDep` commits all rows once.
- Base: a direct scheduler-task test creates a run through a service, commits
  the fixture session, then invokes a worker that opens its own session.
- Good: a scheduler or inventory list route accepts replica delay, injects
  `ReadSessionDep` for its query, and retains primary authentication/RBAC.
- Base: an unset replica host makes a read route use the primary engine without
  allocating another pool.
- Bad: a user/permission or write-following endpoint switches to
  `ReadSessionDep`, a read connection error falls back to primary, a CRUD
  helper commits to make one test pass, a route dispatches Celery before
  commit, or a password-recovery service calls SMTP synchronously in the
  request transaction.

### 6. Tests Required

- Dependency test: assert `SessionDep` and `WriteSessionDep` share one session,
  commit/rollback occurs before close, and all HTTP write routes declare the
  write dependency.
- Read-dependency test: assert `ReadSessionDep` closes without an explicit
  commit or rollback on both success and endpoint failure.
- Configuration/engine test: assert an unset replica host reuses the exact
  primary engine object; a configured host builds a distinct read engine URI
  while preserving the primary port, database, username, and password.
- Dependency-graph test: assert only the reviewed pure-read allowlist uses
  `ReadSessionDep`, it remains `GET`-only, and its auth/RBAC path still uses
  `SessionDep`.
- API regression: assert successful writes commit once and error responses keep
  `detail + request_id` while leaving no partial state.
- Side-effect regression: patch SMTP/broker boundaries and assert they execute
  only after the request commit.
- Direct-caller regression: commit test/worker setup before a second session
  reads it; roll back an expected direct-service failure before querying state.
- E2E: verify an isolated live backend persists a successful write, rejects an
  invalid write without persistence, keeps a manual scheduler run `QUEUED`,
  and preserves authenticated read behavior.

### 7. Wrong vs Correct

#### Wrong

```python
def create_item(*, session: Session, item_in: ItemCreate) -> Item:
    item = Item.model_validate(item_in)
    session.add(item)
    session.commit()
    return item
```

The helper terminates a transaction that may also contain audit, role, or
future outbox changes, so later request failures cannot roll it back.

#### Correct

```python
def create_item(*, session: Session, item_in: ItemCreate) -> Item:
    item = Item.model_validate(item_in)
    session.add(item)
    session.flush()
    return item
```

The HTTP write dependency owns the final commit or rollback. A non-HTTP caller
commits explicitly after the service returns.

#### Wrong

```python
def get_read_db() -> Generator[Session]:
    try:
        with Session(read_engine) as session:
            yield session
    except OperationalError:
        with Session(write_engine) as session:
            yield session
```

This silently hides replica failure, permits a second yield from one
dependency, and breaks the operational contract that a configured read path
must fail observably.

#### Correct

```python
def get_read_db() -> Generator[Session]:
    with Session(read_engine) as session:
        yield session
```

The read boundary only owns its session lifecycle. Engine selection happens at
startup, and a configured replica failure remains observable.

---

## Migration Rules

- Keep SQLModel definitions and Alembic revisions in the same logical change.
- Generate schema changes through Alembic and commit the revision file.
- Review every new-table and add-column operation for the generated table and
  column `comment` values. If autogeneration omits one, add it to that same
  revision before merge.
- After `uv run alembic upgrade head` on an isolated `_test` or `_pytest`
  database, verify the changed table with `obj_description(..., 'pg_class')`
  and each changed column with `col_description(attrelid, attnum)`. Missing or
  non-Chinese comments reject the migration review.
- Treat migration history as part of the contract:
  - [`backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_.py`](../../../backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_.py)
  - [`backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py`](../../../backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py)
- Review generated frontend impact whenever public schemas or endpoint payloads change.

## Scenario: Reconcile Deployed Seed Data

### 1. Scope / Trigger

Apply this when application source adds required permissions or other durable
bootstrap rows that existing databases may already have missed.

### 2. Signatures

Add one forward revision from the current Alembic head. Make the seed operation
idempotent and bind required permissions to the matching built-in role.

### 3. Contracts

- `upgrade()` inserts or updates the canonical seed rows and uses conflict-safe
  association inserts.
- Startup `ensure_bootstrap_state()` remains the reconciliation boundary for
  newly initialized databases and repeated bootstrap runs.
- Custom roles and unrelated role assignments remain unchanged.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Existing database lacks a source-defined permission | Migration creates it and grants it to the required built-in role. |
| Migration runs twice | No duplicate rows or associations are created. |
| Bootstrap runs after seed drift | Missing permission and built-in-role bindings are restored. |
| Custom role has unrelated assignments | Preserve them. |

### 5. Good / Base / Bad Cases

- Good: use `ON CONFLICT` for the permission code and role-permission key.
- Base: a fresh database receives the same rows through normal bootstrap.
- Bad: add a browser-test bypass or silently grant the permission in a route.

### 6. Tests Required

- Test bootstrap after deleting the permission rows and their built-in-role
  associations; assert both the catalog and effective role permissions.
- Upgrade an isolated `_test` database and assert the migration reaches the
  current head and is repeatable.

### 7. Wrong vs Correct

#### Wrong

```python
# Add a scheduler permission only inside a browser fixture or route guard.
```

#### Correct

```sql
INSERT INTO iam_permission (code, group_name, label, description)
VALUES (...) ON CONFLICT (code) DO UPDATE SET description = EXCLUDED.description;
```

The durable seed and its built-in-role binding are repaired at the database
boundary, so normal authorization remains the source of truth.

---

## Scenario: Retiring A Persisted Module

### 1. Scope / Trigger

Apply this when a deployed bounded capability is permanently retired and its
tables, enum types, API routes, configuration, and generated-client contract
must no longer be supported. Existing databases may already be at the prior
head, so deleting the original creation revision is not a valid removal.

### 2. Signatures

Add a forward Alembic revision whose `down_revision` is the current head:

```python
def upgrade() -> None:
    # Drop dependent tables before their parent tables and enum types.
    ...


def downgrade() -> None:
    # Recreate the original empty schema only.
    ...
```

### 3. Contracts

- `upgrade` drops dependent tables first, then parent tables, then module-owned
  enum types or other shared database objects.
- `downgrade` recreates the original columns, indexes, constraints, foreign
  keys, and enum types, but restores no rows. Data recovery belongs to a
  backup/restore procedure, not a schema downgrade.
- Keep the original creation revision immutable. It remains necessary to
  migrate databases that have not yet reached the retirement revision.
- If public routes or schemas are removed with the module, regenerate the
  frontend OpenAPI client; do not hand-edit generated output.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Database at the predecessor revision | Upgrade removes every retired table and enum type. |
| Downgrade to the predecessor revision | Empty tables, indexes, constraints, foreign keys, and enum types are recreated. |
| Re-upgrade to head | The same retired objects are removed again without affecting unrelated schema. |
| Original creation migration is deleted or rewritten | Reject the change; deployed migration history would become invalid. |

### 5. Good / Base / Bad Cases

- Good: a forward revision drops a retired module's child audit table before
  its parent table and then drops its status enums; downgrade recreates only
  the empty audit schema.
- Base: a never-deployed module with no tracked migration can be removed from
  source without a database migration.
- Bad: deleting the original creation revision or using downgrade to reinsert
  historical audit rows.

### 6. Tests Required

- Use a newly created isolated database ending in `_test` or `_pytest`.
- Upgrade to the predecessor revision and inspect that the retired objects
  exist; upgrade to head and inspect that they do not.
- Downgrade to the predecessor revision, verify the recreated objects are
  empty, then re-upgrade to head and verify their absence again.
- For an API-facing retirement, assert the removed route returns the normal
  404/error contract and confirm the regenerated OpenAPI/client lacks the
  retired route and schemas.

### 7. Wrong vs Correct

#### Wrong

```text
Delete the original create_<module>_tables migration with the module source.
```

Existing production databases can no longer resolve their Alembic history.

#### Correct

```text
Keep create_<module>_tables immutable and add remove_<module>_capability as a
forward revision from the current head.
```

The migration chain remains executable for both existing and newly provisioned
databases.

---

## Recommended Direction

- Treat `User` as a stable platform entity.
- Treat `Item` as replaceable or extensible once real domain modeling arrives; do not overfit future architecture around it.
- When adding real business entities, use the new-entity primary-key contract,
  UTC timestamps, explicit public schema wrappers, and matching Alembic revisions.

---

## Cross-Layer Reminder

- If schema or API payloads change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Changes to payload shape should be reviewed together with the frontend forms, query consumers, and page states that use the generated client types.
- Never hand-edit `frontend/src/client/types.gen.ts` as the fix for a backend schema change.

## Scenario: Inventory Decimal Quantities

### 1. Scope / Trigger

- Trigger: inventory counts can be fractional and the same values cross PostgreSQL,
  Pydantic, OpenAPI, generated TypeScript, and Ant Design forms.

### 2. Signatures

- `inventory_document_line.quantity_rolls NUMERIC(18,2) NOT NULL`
- `inventory_ledger_entry.rolls_delta NUMERIC(18,2) NOT NULL`
- Write DTO: `quantity_rolls: Decimal` with `gt=0`, `max_digits=18`, and
  `decimal_places=2`.
- Read DTO: `quantity_rolls: Decimal` with `ge=0`; ledger and balance roll
  fields are also `Decimal`.

### 3. Contracts

- Daily document writes reject zero, negative values, and values with more than
  two decimal places. They do not round the request.
- Historical reads allow `0.00` because controlled legacy imports can contain
  known zero-value rows. The generated OpenAPI client serializes Decimal
  response fields as strings; frontend display and comparisons must account for
  that.
- Migration downgrade must refuse to cast back to integers while fractional
  values exist. Recover from the pre-migration backup instead.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `quantity_rolls = 0`, negative, or has three decimals | HTTP 422 with the standard `detail` and `request_id` shape |
| Legacy row has `quantity_rolls = 0` | Read response is 200; preserve the historical value |
| Source workbook has `0.50` rolls | Import, ledger movement, and reconciliation opening retain `Decimal("0.50")` |
| Downgrade finds a fractional roll | Migration raises; it must not truncate data |

### 5. Good / Base / Bad Cases

- Good: a shipment writes `"0.50"`, creates a `-0.50` ledger movement, and
  the balance aggregation uses `Decimal("0")` as its initial value.
- Base: a pre-existing imported zero-roll shipment can be listed while remaining
  invalid for new document writes.
- Bad: a public read model inherits the write DTO's `gt=0` field, causing a
  response-model validation failure and a list endpoint 500.

### 6. Tests Required

- API tests: accept `0.50`; reject zero, negative, and three-decimal values;
  verify insufficient-inventory behavior still works.
- Importer test: a workbook `0.50` writes a `0.50` line and ledger movement.
- Migration verification: check source-backed repairs, matching reconciliation
  openings, non-negative balances, and downgrade protection on a database copy.
- Frontend: generated-client build succeeds and roll inputs use `min=0.01`,
  `step=0.01`, and `precision=2`.

### 7. Wrong vs Correct

#### Wrong

```python
class InventoryLinePublic(InventoryLineCreate):
    id: uuid.UUID
```

The inherited `gt=0` contract rejects controlled historical zero values when
serializing reads.

#### Correct

```python
class InventoryLinePublic(InventoryLineBase):
    id: uuid.UUID
    quantity_rolls: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
```

Separate read and write contracts so historical compatibility never relaxes new
write validation.

## Scenario: Legacy Workbook Business Dates

- Excel workbooks may store visible dates as numeric serials or as date-formatted
  `datetime` cells. Importers must use the workbook's epoch when converting
  serials; they must not treat a numeric serial as an invalid date.
- Strings matching `YYYY年结存` represent year-end stock and map to
  `YYYY-12-31`. Rows with no business movement may omit a date; rows that create
  a document or ledger entry must fail clearly when their date cannot be parsed.
- Never fall back to `date.today()` for a legacy business date. This would make
  historical ordering and date filters depend on the import execution date.
- A historical date correction migration must update document and ledger dates
  from `legacy_import_row.raw_cells`, run against a database backup, and verify
  document/ledger date equality after migration.

---

## Code Anchors

- Entity models: [`backend/app/models/user.py`](../../../backend/app/models/user.py), [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- API schemas: [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py), [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)
- Service transformations: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Item persistence flow: [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
- Client regeneration script: [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)

## Scenario: Revocable JWT Sessions And Versioned Password Links

### 1. Scope / Trigger

- Trigger: authentication changes cross the FastAPI dependency, SQLModel
  session table, password-link outbox, Alembic migration, and generated
  frontend client.

### 2. Signatures

- `POST /api/v1/login/access-token` returns the existing bearer response and
  creates one `auth_session` row.
- `POST /api/v1/login/logout` accepts the bearer token and revokes only its
  `sid`; it is idempotent for an already revoked or expired session.
- `AuthSession`: `id`, `user_id`, `created_at`, `expires_at`, `revoked_at`.
- `User.password_reset_version` is a non-null integer; link outbox rows keep
  only `password_reset_version`, never reset-token plaintext.

### 3. Contracts

- Access tokens require `sub`, `sid`, `typ=access`, `iss`, `aud`, `iat`, `nbf`,
  and `exp`, use the dedicated access secret, and are checked against an
  active, unexpired `auth_session` on every protected request.
- Password links use the separate password-token secret, `typ` equal to
  `password_reset` or `password_setup`, the user UUID as `sub`, and the
  issuance version. Issuance uses `UPDATE ... SET version = version + 1
  RETURNING version`; consumption conditionally updates the matching version
  and increments it in the same transaction as the password change.
- Password-link outbox retries render from their stored version snapshot.
  Migration-time non-terminal legacy link rows become
  `FAILED/TOKEN_SUPERSEDED`; terminal legacy rows may retain a null version and
  must never be rendered.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Missing, malformed, legacy, wrong issuer/audience/type, revoked, expired, or user-missing access token | `401` with the standard credential error and no write mutation |
| Logout with a valid signed token whose session is missing, expired, or already revoked | `200` no-op |
| Password link version is stale, consumed, expired, or signed for another purpose/secret | `400 Invalid token` and no password/session mutation |
| Password change, reset/setup success, deactivation, or deletion | Revoke all user sessions in the same write transaction |

### 5. Good / Base / Bad Cases

- Good: two logins create two sessions; logout revokes one while the other
  remains usable.
- Base: a migration upgrades a delivered legacy link row without failing, and
  cancels a pending legacy link before delivery can render it.
- Bad: persist an access token, accept a legacy claim shape, or generate a new
  token during a deferred outbox retry.

### 6. Tests Required

- API tests assert required claims, legacy/wrong-claim `401`, single-session
  logout, repeated logout, multi-device behavior, password/account transition
  revocation, and reset/setup single-use/latest-only behavior.
- Outbox tests decode first and retry renderings and assert the same version;
  migration tests cover both terminal legacy rows and
  `TOKEN_SUPERSEDED` cancellation.
- Run focused and full backend tests only against a database ending in
  `_test` or `_pytest`, plus local HTTP login/logout checks.

### 7. Wrong Vs Correct

#### Wrong

```python
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
return session.get(User, payload["sub"])
```

This accepts legacy tokens and never observes server-side session revocation.

#### Correct

```python
payload = security.decode_access_token(token)
user = session.get(User, payload.sub)
auth_session = session.get(AuthSession, payload.sid)
```

Require the complete claim contract, then reject missing, inactive, expired, or
revoked user/session state before returning the user.
