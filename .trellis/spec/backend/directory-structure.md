# Directory Structure

> How backend code is organized in this project.

---

## Overview

Backend code lives under `backend/app` and follows a layered FastAPI layout. Routes stay thin, services hold business rules, CRUD modules own persistence helpers, and SQLModel models/schemas define storage and API contracts.

---

## Directory Layout

```text
backend/
├── app/
│   ├── api/
│   │   ├── deps/
│   │   ├── routes/
│   │   └── main.py
│   ├── core/
│   ├── crud/
│   ├── models/
│   ├── modules/
│   ├── schemas/
│   ├── services/
│   ├── alembic/
│   └── utils.py
├── scripts/
└── tests/
```

---

## Module Organization

- Route registration is centralized in [`backend/app/api/main.py`](../../../backend/app/api/main.py), which imports feature routers from `app/api/routes/**`.
- Route handlers live in files such as [`backend/app/api/routes/users.py`](../../../backend/app/api/routes/users.py) and should mostly validate inputs, attach dependencies, and delegate to services.
- Service-layer logic lives in files such as [`backend/app/services/user.py`](../../../backend/app/services/user.py) and coordinates CRUD, permissions, email side effects, and response shaping.
- Persistence helpers live in files such as [`backend/app/crud/user.py`](../../../backend/app/crud/user.py) and should stay focused on database operations.
- SQLModel table models live in `backend/app/models/**`, while API-facing DTOs live in `backend/app/schemas/**`.
- Cross-cutting runtime code such as config, exceptions, security, and logging lives in `backend/app/core/**`.
- Feature areas that do not fit the main `api/routes` grouping can still expose routers via dedicated modules like [`backend/app/modules/api.py`](../../../backend/app/modules/api.py).

---

## Naming Conventions

- Use singular module names for CRUD and service files when they represent one resource, for example `crud/user.py` and `services/user.py`.
- Keep route files pluralized when the URL space is plural, for example `routes/users.py` and `routes/items.py`.
- Keep schema and model class names resource-oriented, such as `UserCreate`, `UserPublic`, `ItemUpdate`, and `User`.
- Prefer explicit helper names for cross-cutting functions, such as `get_current_active_superuser`, `request_validation_exception_handler`, and `get_datetime_utc`.

---

## Examples

- Route -> service delegation: [`backend/app/api/routes/users.py`](../../../backend/app/api/routes/users.py)
- Service -> CRUD layering: [`backend/app/services/user.py`](../../../backend/app/services/user.py) and [`backend/app/crud/user.py`](../../../backend/app/crud/user.py)
- SQLModel table definitions: [`backend/app/models/user.py`](../../../backend/app/models/user.py) and [`backend/app/models/item.py`](../../../backend/app/models/item.py)
- Dependency and type aliases: [`backend/app/api/deps.py`](../../../backend/app/api/deps.py)
