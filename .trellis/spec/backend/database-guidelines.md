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
- Use UUID `id` fields for durable entity identifiers.
- Use `<resource>_id` for foreign-key fields such as `owner_id`.
- Keep timestamp fields in UTC with timezone-aware storage.
- Public list wrappers should keep the existing `data + count` shape, for example `UsersPublic` and `ItemsPublic`.

---

## Query and Mutation Patterns

- Compose reads with `select(...)`, `where(...)`, `order_by(...)`, `offset(...)`, and `limit(...)`.
- Use `model_validate(...)` to turn ORM objects into public payloads:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Prefer `sqlmodel_update(...)` or `model_dump(exclude_unset=True)` update flows rather than ad hoc patching:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/crud/user.py`](../../../backend/app/crud/user.py)

---

## Migration Rules

- Keep SQLModel definitions and Alembic revisions in the same logical change.
- Generate schema changes through Alembic and commit the revision file.
- Treat migration history as part of the contract:
  - [`backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_to_use_uuid.py`](../../../backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_to_use_uuid.py)
  - [`backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py`](../../../backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py)

---

## Recommended Direction

- Treat `User` as a stable platform entity.
- Treat `Item` as replaceable or extensible once real domain modeling arrives; do not overfit future architecture around it.
- When adding real business entities, keep the same contract discipline: UUID keys, UTC timestamps, explicit public schema wrappers, and matching Alembic revisions.

---

## Cross-Layer Reminder

- If schema or API payloads change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Changes to payload shape should be reviewed together with the frontend forms, query consumers, and page states that use the generated client types.

---

## Code Anchors

- Entity models: [`backend/app/models/user.py`](../../../backend/app/models/user.py), [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- API schemas: [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py), [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)
- Service transformations: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
