# Database Guidelines

> Database patterns and conventions for this project.

---

## Overview

The backend uses SQLModel on top of SQLAlchemy with PostgreSQL. Models are defined in `backend/app/models/**`, request/response DTOs are defined in `backend/app/schemas/**`, and schema changes are tracked with Alembic revisions under `backend/app/alembic/versions/**`.

---

## Query Patterns

- Use `Session.exec(...)` with `select(...)` for read queries, as shown in [`backend/app/services/user.py`](../../../backend/app/services/user.py) and [`backend/app/crud/user.py`](../../../backend/app/crud/user.py).
- Keep query composition explicit with `where(...)`, `order_by(...)`, `offset(...)`, and `limit(...)` instead of hiding logic in generic helpers.
- Build API list responses by transforming ORM rows into public schemas with `model_validate`, for example `UserPublic.model_validate(user)` and `ItemPublic.model_validate(item)`.
- For create/update flows, prefer `model_validate(..., update=...)` and `sqlmodel_update(...)` instead of ad hoc dict unpacking into ORM constructors.
- Keep transactions simple: mutate one or more ORM objects, `session.add(...)` where needed, then `session.commit()` and `session.refresh(...)` for returned entities.

---

## Migrations

- Alembic revisions live under `backend/app/alembic/versions/**`.
- The existing history shows schema evolution through additive revisions such as:
  - [`e2412789c190_initialize_models.py`](../../../backend/app/alembic/versions/e2412789c190_initialize_models.py)
  - [`d98dd8ec85a3_edit_replace_id_integers_in_all_models_to_use_uuid.py`](../../../backend/app/alembic/versions/d98dd8ec85a3_edit_replace_id_integers_in_all_models_to_use_uuid.py)
  - [`fe56fa70289e_add_created_at_to_user_and_item.py`](../../../backend/app/alembic/versions/fe56fa70289e_add_created_at_to_user_and_item.py)
- Local workflow follows the backend README: create a revision after model changes, commit the generated migration, then run `alembic upgrade head`.
- When touching schema shape, keep SQLModel definitions and Alembic history aligned in the same change.

---

## Naming Conventions

- Table names are inferred from SQLModel classes and currently resolve to simple singular names such as `user` and `item`.
- Primary keys use UUIDs stored as `id`.
- Foreign keys follow `<resource>_id`, for example `owner_id`.
- Timestamp fields use `_at` suffixes, for example `created_at`.
- Public schema wrappers follow `<Resource>sPublic` or `<Resource>Public`, for example `UsersPublic` and `ItemsPublic`.

---

## Common Mistakes

- Updating API schemas without checking whether a frontend client regeneration is needed.
- Skipping `session.refresh(...)` when a newly created or updated entity is returned to callers.
- Mixing persistence logic into routes instead of keeping it in CRUD or service layers.
- Making model changes without a matching Alembic revision.
