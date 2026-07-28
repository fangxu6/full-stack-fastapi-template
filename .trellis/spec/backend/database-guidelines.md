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

The service creates rows with the four actor/timestamp values and
`deleted_at=None`. Ordinary updates change only `updated_at` and `updated_by`.
`created_at`, `created_by`, and `deleted_at` are never accepted from public
create or update payloads.

### 3. Contracts

- HTTP mutations obtain the actor from the existing authenticated-user
  dependency. Services receive that actor or its UUID explicitly; repositories
  do not infer it from global state.
- Controlled commands, importers, workers, and scripts must require an
  `actor_user_id: UUID` argument and validate that the user exists before they
  create auditable rows. They must not write `NULL`, a sentinel UUID, or a
  fabricated "system" user.
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
| Command lacks `actor_user_id` | Reject before opening the write transaction with a validation error. |
| Supplied actor does not exist | Reject with the repository's not-found or validation error; do not persist a row. |
| Client sends a creator or updater field in a public payload | Ignore no values silently: reject the payload schema as unsupported. |
| Client sends `deleted_at` in a create or ordinary update payload | Reject the payload schema as unsupported; use the explicit delete or restore operation. |
| Update tries to alter a creator field | Reject as a validation or domain error; preserve the original values. |
| User deletion is blocked by an audit reference | Surface a semantic conflict; require deactivation rather than physical deletion. |

### 5. Good / Base / Bad Cases

- Good: a receipt is created by the authenticated user. Both creator and updater
  IDs are that user's UUID, and both timestamps use the same UTC instant.
- Base: editing the receipt changes only the updater pair; the creator pair
  remains unchanged.
- Bad: an Excel importer writes rows with `created_by = NULL` because it
  runs outside HTTP. The importer must instead require the operator's UUID.

### 6. Tests Required

- Insert test: assert all four actor/timestamp fields are non-null, the two
  creator/updater pairs are equal on creation, and `deleted_at` is `NULL`.
- Update test: assert only the updater pair changes, while creator fields remain
  unchanged.
- Soft-delete/restore test: assert delete sets a UTC `deleted_at` value and
  changes the updater pair; restore sets it back to `NULL` without changing
  creator fields.
- Authorization/command test: assert unauthenticated mutation and a command
  without an actor fail before inserting any business rows.
- Referential-integrity test: assert physical deletion of a referenced user is
  rejected, while user deactivation preserves historical rows.
- Migration test: assert every new in-scope table contains the five audit
  columns, UTC timestamp types, non-null constraints, and two foreign keys to
  `user.id`.

### 7. Wrong vs Correct

#### Wrong

```python
document = InventoryDocument(
    created_by=payload.created_by,
    updated_by=payload.updated_by,
)
```

This lets a caller forge audit history and leaves command-driven writes without
an accountable actor.

#### Correct

```python
now = get_datetime_utc()
document = InventoryDocument(
    created_at=now,
    created_by=current_user.id,
    updated_at=now,
    updated_by=current_user.id,
)
```

For a later mutation, obtain the current actor again and change only
`updated_at` and `updated_by` in the same transaction as the business
change.

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

Apply this to every FastAPI `POST`, `PUT`, `PATCH`, and `DELETE` route. The
request owns one transaction shared by authentication, permission, route, and
service dependencies. Read routes retain the read-only session dependency.

### 2. Signatures

```python
SessionDep = Annotated[Session, Depends(get_db, scope="function")]


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

`get_db()` remains the only request session factory and closes the session.
Both dependency signatures use the same callable and `scope="function"` so
FastAPI reuses one cached `Session` and finalizes it before response sending.

### 3. Contracts

- Every HTTP write handler declares `WriteSessionDep`, including a write-method
  endpoint that currently only authenticates or reads.
- `SessionDep` remains the dependency for reads and authentication/RBAC
  dependencies. It must use the same function scope as `WriteSessionDep`.
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
| Expected unique/integrity conflict | Flush and convert it to the existing domain error before final commit; the dependency performs the rollback. |
| Direct test setup calls an HTTP route or worker that opens another session | Commit setup data first. After an expected direct-service exception, roll back before asserting durable state. |
| Direct setup retains a row lock and calls a second-session worker | Commit before the worker call so it can read or update the same row without blocking. |

### 5. Good / Base / Bad Cases

- Good: a route creates a user, role links, and an item through services that
  flush, then `WriteSessionDep` commits all rows once.
- Base: a direct scheduler-task test creates a run through a service, commits
  the fixture session, then invokes a worker that opens its own session.
- Bad: a CRUD helper commits to make one test pass, a route dispatches Celery
  before commit, or a password-recovery service calls SMTP synchronously in
  the request transaction.

### 6. Tests Required

- Dependency test: assert `SessionDep` and `WriteSessionDep` share one session,
  commit/rollback occurs before close, and all HTTP write routes declare the
  write dependency.
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

---

## Migration Rules

- Keep SQLModel definitions and Alembic revisions in the same logical change.
- Generate schema changes through Alembic and commit the revision file.
- Treat migration history as part of the contract:
  - [`backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_.py`](../../../backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_.py)
  - [`backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py`](../../../backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py)
- Review generated frontend impact whenever public schemas or endpoint payloads change.

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
