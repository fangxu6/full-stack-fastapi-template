# Modularize backend items boundary

## Goal

Turn the existing `items` backend flow into the first modular-backend pilot while preserving the public API contract. The pilot should prove that a bounded backend capability can live under `backend/app/modules/items/` without changing `/api/v1/items/*` behavior.

## Requirements

- Keep `backend/app/api/routes/items.py` as the public HTTP route owner so paths, tags, schema names, and operation IDs stay stable.
- Add `backend/app/modules/items/` as the internal item module boundary.
- Move item business orchestration into module-local service code.
- Move item persistence helpers into module-local repository code.
- Make item transaction ownership service-level: repository and `crud.item` helpers must not commit.
- Limit the transaction-boundary contract change to items; do not change users/auth CRUD behavior in this task.
- Preserve the unified error contract with `detail` and `request_id`.
- Record durable architecture decisions in ADRs.

## Acceptance Criteria

- [x] `items` API tests still pass for create, read, update, delete, not found, permission failure, and trailing-slash compatibility.
- [x] Item CRUD/repository tests prove helper functions do not commit automatically.
- [x] OpenAPI output has zero diff for the migration.
- [x] Backend lint/type gate passes for changed files; full bash wrapper is unavailable on this Windows host and repo-wide direct checks still have pre-existing unrelated failures.
- [x] Backend test suite passes with direct `uv run pytest tests/` execution.
- [x] ADRs document modular monolith direction and item service transaction ownership.

## Out of Scope

- Moving `users` or `auth` into `modules/iam/`.
- Moving route declarations out of `api/routes/items.py`.
- Changing database models, API schemas, Alembic migrations, or generated frontend client code.
- Introducing full Clean Architecture, ports/adapters, CQRS, event bus, or microservices.
