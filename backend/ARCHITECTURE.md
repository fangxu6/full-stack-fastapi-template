# Backend Architecture

This document describes the current backend architecture after the Enterprise Scaffold batch-0 baseline work. It reflects the live code under `backend/app`, not the older single-file template layout.

## 1. Current Structure

```text
backend/
├── app/
│   ├── alembic/                    # Database migrations
│   ├── api/
│   │   ├── dependencies/          # Modular dependency injection (auth, db session)
│   │   ├── routes/                # HTTP route files
│   │   ├── deps.py                # Backward-compatible dependency entrypoint
│   │   └── main.py                # API router aggregation
│   ├── core/                      # Cross-cutting platform capabilities
│   │   ├── config.py              # Settings and environment parsing
│   │   ├── db.py                  # Engine/bootstrap integration
│   │   ├── exceptions.py          # Request ID middleware + unified error handling
│   │   ├── logging.py             # Central logging entrypoint placeholder
│   │   ├── observability.py       # Platform observability placeholder
│   │   ├── pagination.py          # Shared pagination placeholder
│   │   └── security.py            # JWT/password security helpers
│   ├── crud/                      # Atomic persistence operations
│   ├── infra/                     # Infrastructure boundary placeholders
│   │   └── db/
│   ├── models/                    # SQLModel ORM entities only
│   ├── modules/                   # Module boundary skeleton
│   │   ├── api.py                 # Modules router aggregation entrypoint
│   │   ├── audit/
│   │   ├── file/
│   │   ├── iam/
│   │   └── system/
│   ├── schemas/                   # API request/response contracts
│   ├── services/                  # Business orchestration layer
│   ├── utils.py                   # Shared helper functions (email, misc)
│   └── main.py                    # FastAPI application entrypoint
└── tests/
```

## 2. Architectural Intent

The backend is moving from a template-style layout toward a platformized structure with explicit boundaries:

- `api/*`: HTTP transport layer
- `services/*`: business orchestration
- `crud/*`: atomic data access
- `models/*`: ORM entities
- `schemas/*`: API contracts
- `core/*`: reusable cross-cutting platform capabilities
- `infra/*`: infrastructure abstractions
- `modules/*`: future business-domain module boundaries

Today, most real business logic still lives in `services/*`, but new platform seams already exist and should be preferred for incremental growth.

## 3. Request Flow

### Main application flow

```text
app/main.py
  -> RequestIdMiddleware
  -> exception handlers (AppError / HTTPException / validation / unhandled)
  -> app/api/main.py
  -> app/api/routes/* and app/modules/api.py
```

### Standard business flow

```text
Route
  -> dependency resolution (auth / db)
  -> service
  -> crud
  -> model / database
```

Not every route hits every layer, but new backend work should preserve this direction and avoid pushing business rules back into route handlers.

## 4. Error and Observability Baseline

The batch-0 backend baseline introduced a shared error contract in `app/core/exceptions.py`.

### What is centralized

- `RequestIdMiddleware`
- `AppError` hierarchy
- structured handling for:
  - domain/application errors
  - framework `HTTPException`
  - `RequestValidationError`
  - unhandled `500`

### Required response contract

All error responses should converge on:

```json
{
  "detail": "...",
  "request_id": "..."
}
```

### Required logging behavior

Unhandled exceptions must not be swallowed silently:

- the client gets a generic `500`
- the response still includes `request_id`
- server logs retain traceback and request path

This is now part of the backend architecture, not a route-level convention.

## 5. Dependency Boundaries

### `api/dependencies/*`

This layer owns reusable request-scoped dependencies such as:

- database session resolution
- current user lookup
- superuser enforcement

Authentication and authorization logic should be reused from here instead of reimplemented per route.

### `core/security.py`

JWT creation, password hashing, password verification, and related security primitives stay centralized here.

### `models/*` vs `schemas/*`

The repository has already adopted the rule that:

- `models/*` exports ORM entities only
- `schemas/*` exports API DTOs only

Do not mix schema imports back into the ORM layer.

## 6. Module Growth Guidance

The `modules/*` tree is currently a scaffold, not a fully migrated module system. That is intentional.

When adding a new backend capability:

1. decide whether it is cross-cutting (`core`), infra (`infra`), or domain-facing (`modules`)
2. expose HTTP entrypoints from `api/*` or a module router
3. implement orchestration in `services/*` or module-local services
4. reuse the shared exception contract
5. add tests for success, auth, validation, and not-found/error paths

Do not treat `modules/*` as dead weight and route around it by expanding ad-hoc global files forever.

## 7. Current Risks and Transitional Reality

- `modules/*` and `infra/*` are still mostly placeholders; the structure is ahead of full migration.
- Several business flows are still carried by the legacy `services/*` + `crud/*` model.
- The architecture is therefore intentionally hybrid: stable enough for new work, but not yet fully domain-modular.

That means new changes should move with the target boundary, not reinforce the old flat shape.
