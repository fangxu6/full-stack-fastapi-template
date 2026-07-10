# Backend Development Guidelines

> Repo-specific guidance for the FastAPI + SQLModel backend in `backend/app/**`.

---

## Overview

This backend is no longer just the upstream template. It is in a platform-batch-0 transition toward a more enterprise-ready scaffold:

- unified exception handling and `request_id` correlation are already implemented
- `core/*`, `infra/*`, and `modules/*` establish the intended backend boundaries
- most real business behavior still lives in `services/*` and `crud/*`

Future work should preserve that direction instead of drifting back toward route-heavy or monolithic helper patterns.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Layer ownership, placement rules, transitional structure | Customized |
| [Database Guidelines](./database-guidelines.md) | SQLModel entities, API schemas, Alembic workflow | Customized |
| [Error Handling](./error-handling.md) | Unified error contract and exception usage | Customized |
| [Type Safety](./type-safety.md) | Python 3.14, SQLModel/Pydantic, service signatures, and generated-client impact | Customized |
| [Quality Guidelines](./quality-guidelines.md) | Review rules, forbidden regressions, validation expectations | Customized |
| [Logging Guidelines](./logging-guidelines.md) | Request correlation and operational logging minimums | Customized |

---

## Read Order

1. Read [Directory Structure](./directory-structure.md) before choosing file placement.
2. Read [Database Guidelines](./database-guidelines.md) before touching models, schemas, or migrations.
3. Read [Type Safety](./type-safety.md) before changing public schemas, service signatures, UUID/datetime behavior, or OpenAPI-visible payloads.
4. Read [Error Handling](./error-handling.md) and [Logging Guidelines](./logging-guidelines.md) before changing API or service behavior.
5. Use [Quality Guidelines](./quality-guidelines.md) as the final backend review checklist.

### Trigger-Based Routing

| Trigger | Required Reads |
| --- | --- |
| New route or route behavior change | [Directory Structure](./directory-structure.md), [Error Handling](./error-handling.md), [Quality Guidelines](./quality-guidelines.md) |
| Model, schema, or migration change | [Database Guidelines](./database-guidelines.md), [Type Safety](./type-safety.md) |
| Expected error or auth/permission failure change | [Error Handling](./error-handling.md), [Logging Guidelines](./logging-guidelines.md), [Quality Guidelines](./quality-guidelines.md) |
| Public API payload or OpenAPI output change | [Type Safety](./type-safety.md), [Database Guidelines](./database-guidelines.md), [../guides/cross-layer-thinking-guide.md](../guides/cross-layer-thinking-guide.md) |
| New bounded backend capability | [Directory Structure](./directory-structure.md), [../guides/code-reuse-thinking-guide.md](../guides/code-reuse-thinking-guide.md) |

---

## Current Reality

- The request pipeline is already standardized through [`backend/app/main.py`](../../../backend/app/main.py) and [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py).
- Real domain behavior is still service-first:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- `modules/*` and `infra/*` exist as future-facing boundaries:
  - [`backend/app/modules/api.py`](../../../backend/app/modules/api.py)
  - [`backend/app/modules/system/__init__.py`](../../../backend/app/modules/system/__init__.py)
  - [`backend/app/infra/db/session.py`](../../../backend/app/infra/db/session.py)
- `Item` is still a template-style entity rather than a fully business-specific domain model:
  - [`backend/app/models/item.py`](../../../backend/app/models/item.py)
  - [`backend/app/schemas/item.py`](../../../backend/app/schemas/item.py)

---

## Recommended Direction

- Keep route handlers thin and continue concentrating business rules in services until real module-local service slices emerge.
- Add new cross-cutting behavior to `core/*`, not to ad hoc helpers spread across routes or services.
- When introducing a new business module, prefer attaching it to `modules/*` as an explicit boundary instead of growing one more large shared file. Keep simple CRUD in the lightweight route/service/crud flow until that boundary is justified.
- Preserve the unified error contract and `request_id` chain as non-optional platform behavior.

---

## Local Dev Defaults

- Install deps from `backend/`: `uv sync`
- Run tests from `backend/`: `uv run pytest tests/`
- Lint: `bash backend/scripts/lint.sh`
- Format: `bash backend/scripts/format.sh`
- Type checks are configured in [`backend/pyproject.toml`](../../../backend/pyproject.toml):
  Python is `>=3.14,<4.0`, mypy is strict, Ruff targets `py314`, and `ty`
  treats warnings as errors.
- Preferred backend quality gate from repo root: `bash backend/scripts/lint.sh`.
- Full-stack test flow from repo root: `bash ./scripts/test.sh`
- Running stack tests from repo root: `docker compose exec backend bash scripts/tests-start.sh`

Assume backend verification uses `http://127.0.0.1:8000` unless the task says otherwise.

---

## Cross-Layer Reminder

- If backend request/response contracts change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Error responses must continue to expose both `detail` and `request_id`, because frontend troubleshooting depends on that contract.
- Do not manually patch `frontend/src/client/**` to compensate for backend schema changes; regenerate it from OpenAPI.

---

## Code Anchors

- App setup and exception registration: [`backend/app/main.py`](../../../backend/app/main.py)
- Unified exception and request-id flow: [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Service-layer domain behavior: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Backend tooling: [`backend/pyproject.toml`](../../../backend/pyproject.toml)
- Client regeneration: [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
