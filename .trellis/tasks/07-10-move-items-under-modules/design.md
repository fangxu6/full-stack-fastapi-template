# Keep items on lightweight CRUD design

## Architecture

The current project is mostly CRUD-oriented, so `items` should use the lightweight path described by `3. Python后端架构规则-ORM隔离与实用边界.md`:

```text
api/routes/items.py -> services/item.py -> crud/item.py -> ORM
```

This avoids Clean Architecture ceremony for a simple table-backed resource while preserving thin routes, service-owned business checks, and CRUD-owned SQLModel access.

## Route Contract

- Public route: `/api/v1/items/*`
- No public module route: `/api/v1/modules/items/*`
- Existing item request/response schemas remain unchanged.
- Existing error contract remains unchanged through global exception handlers.

## Code Boundaries

- `api/routes/items.py`: HTTP path operation declarations.
- `services/item.py`: item business rules, permissions, transaction commit/refresh.
- `crud/item.py`: SQLModel persistence operations without commit.
- `modules/items/*`: not used for this simple CRUD resource.

## Frontend Impact

OpenAPI should expose item URLs under `/api/v1/items/*`. Regenerate the frontend client and keep item feature consumers on the generated `ItemsService`.

## Module Escalation Rule

Promote a domain into `modules/*` only after it develops multi-table workflows, state transitions, background tasks, external-system calls, events, or cross-module collaboration.
