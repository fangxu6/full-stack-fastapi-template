# Directory Structure

> How backend code is organized in this repository today, and how new code should fit into it.

---

## Overview

Backend code lives under `backend/app`. This repo uses a hybrid architecture:
simple CRUD follows the established `api -> services -> crud -> models/schemas`
flow, while operational domains own module-local boundaries when their workflow
earns them.

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

- `api/*` is the shared HTTP aggregation layer:
  - router assembly in [`backend/app/api/main.py`](../../../backend/app/api/main.py)
  - route handlers in [`backend/app/api/routes/users.py`](../../../backend/app/api/routes/users.py) and [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py)
  - local-only private routes are included conditionally from [`backend/app/api/main.py`](../../../backend/app/api/main.py)
- `services/*` carries lightweight CRUD and shared business orchestration:
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
- `modules/*` owns operational domain boundaries alongside conventional routes:
  - [`backend/app/modules/inventory/router.py`](../../../backend/app/modules/inventory/router.py)
  - [`backend/app/modules/iam/router.py`](../../../backend/app/modules/iam/router.py)
  - [`backend/app/modules/scheduler/router.py`](../../../backend/app/modules/scheduler/router.py)
- `infra/*` owns reusable infrastructure concerns when they are justified:
  - [`backend/app/infra/db/session.py`](../../../backend/app/infra/db/session.py)

---

## Layer Ownership Rules

- Put request parsing, dependency wiring, and response declarations in `api/*` for simple CRUD/global routes or in `modules/<name>/router.py` only when the module boundary is justified.
- Put business rules, permission checks, orchestration, and cross-entity flows in `services/*`.
- Put database-focused create/read/update/delete helpers in `crud/*`.
- Put SQLModel tables in `models/*` and API payload schemas in `schemas/*`.
- Put configuration, security, exception handling, logging, and similar cross-cutting behavior in `core/*`.
- Put module-boundary entrypoints in `modules/*` when introducing a business slice with enough complexity that it should not remain a lightweight CRUD addition.
- For items, keep public route declarations in `api/routes/items.py` and the lightweight `router -> service -> crud -> ORM` flow.
- Put infra abstractions in `infra/*` only when they represent reusable infrastructure concerns rather than business logic.
- Keep startup/lifecycle scripts such as `backend_pre_start.py` and `initial_data.py` small and operational; do not hide request-time business behavior there.

## Architecture Escalation

Start with the lightest existing boundary that satisfies the workflow. Use
`api/routes/items.py`, `services/item.py`, and `crud/item.py` as the concrete
simple-CRUD reference. Promote a domain into `modules/*` only after it develops
multi-table workflows, state transitions, durable asynchronous work,
external-system calls, events, or cross-module collaboration.

When a `modules/*` domain design meets the workflow trigger described in the
[State Transition Design Guidelines](./state-transition-guidelines.md), keep
the state transition matrix in the domain design documentation before coding.
The matrix documents the domain boundary; it does not justify a shared runtime,
registry, or extra layer.

| Concern | Default for lightweight CRUD | Upgrade only when | Do not add by default |
| --- | --- | --- | --- |
| Entity | SQLModel model plus service-enforced rules | Business invariants must be reused independently of persistence | A separate domain entity or ORM mapper |
| Use case | A focused function in `services/*` | A module owns complex orchestration, state transitions, or cross-domain work | One use-case class per endpoint |
| DTO / adapter | Pydantic schemas at HTTP, task, and event boundaries | An external protocol needs translation or an integration is genuinely replaceable | Mappers or adapters between internal layers |
| DI | FastAPI `Depends` for request-scoped dependencies | A replaceable external client or complex lifecycle needs constructor injection | A DI container or service locator |

New backend features should not be dumped into a single expanding `crud.py` or
thick route files. Conversely, named patterns alone do not earn a module or a
new layer: the observable workflow complexity must justify it.

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
- Operational module boundaries: [`backend/app/modules/inventory/router.py`](../../../backend/app/modules/inventory/router.py), [`backend/app/modules/iam/router.py`](../../../backend/app/modules/iam/router.py), [`backend/app/modules/scheduler/router.py`](../../../backend/app/modules/scheduler/router.py)
- Lightweight item CRUD: [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
