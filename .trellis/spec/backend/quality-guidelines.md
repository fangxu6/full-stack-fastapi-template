# Quality Guidelines

> Backend review and regression guardrails for this repository.

---

## Overview

Backend quality in this repo is mostly about preserving architectural direction:

- keep routes thin
- keep services explicit
- preserve unified errors and request correlation
- keep model/schema/API changes synchronized with frontend contract regeneration

---

## Required Patterns

- Keep layering explicit: `api route -> service -> crud -> models/schemas` for simple CRUD; use `module router -> module service -> module repository` only when a domain earns that boundary.
- Use semantic application exceptions for expected business failures.
- Keep new platform-wide behavior in `core/*`.
- Keep model/schema changes paired with migration thinking and frontend client impact review.
- Use explicit typing and current SQLModel update/validation patterns.
- Follow backend tooling configured in [`backend/pyproject.toml`](../../../backend/pyproject.toml): strict mypy, Ruff, `ty`, and pytest.

---

## Strong Review Rules

- New module work should attach to the existing platform skeleton rather than expanding one large shared file forever.
- If a feature is simple CRUD, keep it lightweight. If it suggests a bounded business slice, prefer a deliberate path through `modules/*` over uncontrolled growth in route files or a giant `crud.py`.
- For items, keep the public router at `api/routes/items.py`, service behavior at `services/item.py`, and persistence helpers at `crud/item.py`; the public path remains `/api/v1/items/*`.
- API contract changes require checking whether `bash ./scripts/generate-client.sh` must be run.
- New or changed error branches should preserve the `detail + request_id` response contract.
- Large files are a review smell. If a route, service, or helper grows because it owns several unrelated responsibilities, split by boundary before adding more behavior.
- Comments should explain why, invariants, compatibility constraints, rollback notes, or side effects. Do not add comments that merely restate the next line of code.
- Reads that will later feed pagination, counts, or bulk mutation should be reviewed for N+1 queries and Python-side filtering of full tables.
- Offset-paginated routes must reject invalid offsets and page sizes at the
  route boundary before database access. List queries must use a deterministic
  order that ends with a unique tie-breaker; their `count` and page queries
  must apply the same visibility and filter predicates. The current `items`
  contract is `skip >= 0`, `1 <= limit <= 100`, ordered by
  `created_at DESC, id DESC`.
- Public schema changes should include a documentation/client-sync decision: generated client, frontend consumers, and feature docs are either updated or explicitly not affected.

---

## Minimum Validation Expectations

- Preferred backend gate: `bash backend/scripts/lint.sh` from the repo root, which runs strict mypy, `ty check app`, Ruff, and Ruff format check.
- Preferred backend test command from `backend/`: set `POSTGRES_DB=aiadmin_test`, then run `bash scripts/test.sh` or a focused `uv run pytest ...` when the full suite is not appropriate. `aiadmin_test` is the required isolated database for destructive backend tests and local API E2E; never point either workflow at the development database.
- If a backend change affects error behavior, verify at least one path that exercises the unified error shape.
- If auth, permission, or validation behavior changes, verify the relevant `401`, `403`, or `422` contract path.
- If request/response models change, review frontend generated-client impact before closing the task.
- If OpenAPI output changes, run `bash ./scripts/generate-client.sh` or explicitly document why regeneration was not required.
- If tests are skipped, say so explicitly in the handoff.

### Scenario: Isolated PostgreSQL Test Database

#### 1. Scope / Trigger

- Trigger: running any backend pytest suite, focused destructive test, or local
  API E2E flow that initializes or clears PostgreSQL data.

#### 2. Signatures

```bash
POSTGRES_DB=aiadmin_test bash scripts/test.sh
POSTGRES_DB=aiadmin_test uv run pytest tests/<path>
```

#### 3. Contracts

- `aiadmin_test` is the project's local isolated PostgreSQL database for
  destructive backend tests and API E2E.
- The database must exist before pytest runs; the session fixture upgrades it
  to the Alembic head and clears its supported test tables after the suite.
- `POSTGRES_DB=aiadmin` is development data and must never be used for tests.

#### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| `POSTGRES_DB=aiadmin_test` and the database exists | Run migrations and tests. |
| Name is `aiadmin`, blank, or a system database | Refuse before destructive test setup. |
| Name has a safe suffix but the database does not exist | Fail during connection/migration; create the isolated database, never substitute the development database. |

#### 5. Good / Base / Bad Cases

- Good: a focused backend test exports `POSTGRES_DB=aiadmin_test` and leaves
  `aiadmin` untouched.
- Base: the fixture clears its known tables after a successful suite.
- Bad: pointing pytest at `aiadmin` to avoid creating the test database.

#### 6. Tests Required

- Verify the database guard rejects `aiadmin` before migrations run.
- Verify CI/local test commands set `POSTGRES_DB=aiadmin_test` before pytest.

#### 7. Wrong Vs Correct

#### Wrong

```bash
POSTGRES_DB=aiadmin uv run pytest tests/core/test_config.py
```

#### Correct

```bash
POSTGRES_DB=aiadmin_test uv run pytest tests/core/test_config.py
```

---

## Delivery Gate Checklist

- [ ] Route handlers remain thin and delegate business behavior to services.
- [ ] Expected failures use semantic application exceptions or framework errors that still pass through the unified handlers.
- [ ] Error responses still include `detail` and `request_id`.
- [ ] New logs avoid secrets and preserve enough context to correlate with `request_id`.
- [ ] Model/schema changes include Alembic and generated-client review.
- [ ] Bulk/list behavior is checked for N+1 and full-table-in-Python filtering.
- [ ] Documentation or `.trellis/spec/**` updates are considered when a reusable rule or gotcha was learned.

---

## Forbidden Patterns

- Thick route handlers with business orchestration
- New ad hoc error payload shapes
- Model or schema changes without migration review
- Backend contract changes that ignore frontend SDK regeneration needs
- Unrelated mass formatting while touching backend files
- Manual edits under `frontend/src/client/**` to work around backend typing issues

---

## Current Reality vs Recommended Direction

### Current reality

- Real business behavior is concentrated in:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Unified error behavior is already implemented through:
  - [`backend/app/main.py`](../../../backend/app/main.py)
  - [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)

### Recommended direction

- Continue migrating toward explicit module boundaries without pretending `modules/*` is already mature.
- Use review pressure to stop regression back into the looser template-era structure.

---

## Code Anchors

- Service-first behavior: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Error baseline: [`backend/app/main.py`](../../../backend/app/main.py), [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Model/schema contract examples: [`backend/app/models/user.py`](../../../backend/app/models/user.py), [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- Lightweight item CRUD: [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
- Backend and cross-layer tooling: [`backend/pyproject.toml`](../../../backend/pyproject.toml), [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
