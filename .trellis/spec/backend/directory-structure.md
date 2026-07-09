# Directory Structure

> How backend code is organized in this repository today, and how new code should fit into it.

---

## Overview

Backend code lives under `backend/app`. This repo is in a transitional architecture state: the target boundaries (`core`, `infra`, `modules`) exist, but most concrete business behavior is still implemented through the established `api -> services -> crud -> models/schemas` flow.

---

## Current Reality

```text
backend/app/
├── api/
├── core/
├── crud/
├── infra/
├── models/
├── modules/
├── schemas/
├── services/
├── alembic/
└── utils.py
```

- `api/*` is the HTTP layer:
  - router assembly in [`backend/app/api/main.py`](../../../backend/app/api/main.py)
  - route handlers in [`backend/app/api/routes/users.py`](../../../backend/app/api/routes/users.py) and [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py)
  - local-only private routes are included conditionally from [`backend/app/api/main.py`](../../../backend/app/api/main.py)
- `services/*` currently carries most business behavior:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- `crud/*` owns direct persistence helpers:
  - [`backend/app/crud/user.py`](../../../backend/app/crud/user.py)
  - [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
- `models/*` and `schemas/*` split storage and API contracts:
  - [`backend/app/models/user.py`](../../../backend/app/models/user.py)
  - [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- `core/*` already contains real platform-level behavior such as config, security, and exception handling:
  - [`backend/app/core/config.py`](../../../backend/app/core/config.py)
  - [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- `modules/*` and `infra/*` are still mostly boundary skeletons:
  - [`backend/app/modules/api.py`](../../../backend/app/modules/api.py)
  - [`backend/app/modules/items/service.py`](../../../backend/app/modules/items/service.py)
  - [`backend/app/modules/items/repository.py`](../../../backend/app/modules/items/repository.py)
  - [`backend/app/infra/db/session.py`](../../../backend/app/infra/db/session.py)

---

## Layer Ownership Rules

- Put request parsing, dependency wiring, and response declarations in `api/*`.
- Put business rules, permission checks, orchestration, and cross-entity flows in `services/*`.
- Put database-focused create/read/update/delete helpers in `crud/*`.
- Put SQLModel tables in `models/*` and API payload schemas in `schemas/*`.
- Put configuration, security, exception handling, logging, and similar cross-cutting behavior in `core/*`.
- Put module-boundary entrypoints in `modules/*` when introducing a new business slice that should not remain an unbounded service-only addition.
- For the item module pilot, keep public route declarations in `api/routes/items.py` while module-local service and repository code live in `modules/items/*`.
- Put infra abstractions in `infra/*` only when they represent reusable infrastructure concerns rather than business logic.
- Keep startup/lifecycle scripts such as `backend_pre_start.py`, `tests_pre_start.py`, and `initial_data.py` small and operational; do not hide request-time business behavior there.

---

## Recommended Direction

- New backend features should not be dumped back into a single expanding `crud.py` or into thick route files.
- If a feature starts forming its own boundary, add it deliberately under `modules/<name>/` and let that boundary grow over time.
- Until `modules/*` becomes richer, keep using the existing service-first pattern rather than inventing parallel placement rules.
- Use `modules/items/*` as the first concrete reference for a module-local service/repository boundary; do not route public endpoints through the existing `/modules` router unless the public URL is intentionally changing.

---

## Forbidden Regressions

- Do not move business orchestration into route handlers.
- Do not bypass `core/*` for cross-cutting exception or request-tracing behavior.
- Do not treat `modules/*` as a junk drawer for random files with no boundary story.
- Do not duplicate service-layer rules in CRUD helpers just because multiple routes need the same check.

---

## Code Anchors

- Router assembly: [`backend/app/api/main.py`](../../../backend/app/api/main.py)
- Thin route examples: [`backend/app/api/routes/login.py`](../../../backend/app/api/routes/login.py), [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py), [`backend/app/api/routes/docs.py`](../../../backend/app/api/routes/docs.py)
- Real service-first business flow: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/services/docs.py`](../../../backend/app/services/docs.py)
- Transitional module skeleton: [`backend/app/modules/api.py`](../../../backend/app/modules/api.py), [`backend/app/modules/system/__init__.py`](../../../backend/app/modules/system/__init__.py)
- Item module pilot: [`backend/app/modules/items/service.py`](../../../backend/app/modules/items/service.py), [`backend/app/modules/items/repository.py`](../../../backend/app/modules/items/repository.py)
