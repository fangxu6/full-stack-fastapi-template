# Quality Guidelines

> Backend review and regression guardrails for this repository.

---

## Overview

Backend quality in this repo is mostly about preserving architectural direction:

- keep routes thin
- select boundaries by workflow complexity
- preserve unified errors and request correlation
- keep model/schema/API changes synchronized with frontend contract regeneration

---

## Required Patterns

- Keep layering explicit: use the two supported paths and escalation triggers in [Directory Structure](./directory-structure.md#architecture-escalation).
- Use semantic application exceptions for expected business failures.
- Keep new platform-wide behavior in `core/*`.
- Keep model/schema changes paired with migration thinking and frontend client impact review.
- Use explicit typing and current SQLModel update/validation patterns.
- Follow backend tooling configured in [`backend/pyproject.toml`](../../../backend/pyproject.toml): strict mypy, Ruff, `ty`, and pytest.

---

## Strong Review Rules

- New module work should attach to an operational domain boundary rather than expanding one large shared file forever.
- If a feature is simple CRUD, keep it lightweight. If it earns a bounded business slice, use `modules/*`; do not introduce separate entities, use-case classes, adapters, repository interfaces, or a DI container unless the matching trigger in [Directory Structure](./directory-structure.md#architecture-escalation) applies.
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

- On Windows, use the Bash flow in [Windows Bash Quality Commands](#scenario-windows-bash-quality-commands). It changes to `backend/` before running a backend script.
- The preferred non-mutating backend gate is `cd backend && bash scripts/lint.sh`, which runs strict mypy, `ty check app`, Ruff, and Ruff format check. The script requires `backend/` as its current directory because it passes `app` as a relative path.
- Preferred backend test command from `backend/`: use the ignored local root `.env_test` with `uv run --env-file ../.env_test pytest ...` when available, or set `POSTGRES_DB=aiadmin_test` explicitly. `aiadmin_test` is the default isolated database for destructive backend tests and local API E2E; a pre-created database whose name ends in `_test` or `_pytest` is also valid for a clean or concurrent verification run. Never point either workflow at the development database.
- If a backend change affects error behavior, verify at least one path that exercises the unified error shape.
- If auth, permission, or validation behavior changes, verify the relevant `401`, `403`, or `422` contract path.
- If request/response models change, review frontend generated-client impact before closing the task.
- If OpenAPI output changes, run `bash ./scripts/generate-client.sh` or explicitly document why regeneration was not required.
- If tests are skipped, say so explicitly in the handoff.

### Scenario: Windows Bash Quality Commands

#### 1. Scope / Trigger

- Trigger: running backend lint, type checks, formatting checks, or pytest from
  Windows PowerShell on this workstation.

#### 2. Signatures

From the repository root, run the non-mutating quality gate through the
default `bash` executable:

```powershell
bash -lc 'cd backend && ./scripts/lint.sh'
```

For a focused test, first select the isolated database:

```powershell
$env:POSTGRES_DB = 'aiadmin_test'
bash -lc 'cd backend && uv run pytest tests/<path>'
```

#### 3. Contracts

- The default `bash` executable is the Windows shell entry point for backend
  Bash commands. It must resolve the project's `uv` toolchain.
- Do not hard-code a machine-specific Bash installation path in shared docs or
  automated commands.
- `backend/scripts/lint.sh` requires `backend/` as its current directory. Do
  not call `bash backend/scripts/lint.sh` from the repository root.
- `backend/scripts/format.sh` currently calls `ruff` directly rather than
  `uv run ruff`; the default Bash environment cannot resolve that command in
  this workspace. Until the script is made toolchain-aware, run the equivalent
  `uv run ruff` format commands explicitly instead of claiming the script is a
  Windows entry point.

#### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Windows backend lint or type check | Invoke `bash -lc 'cd backend && ./scripts/lint.sh'`. |
| `mypy` cannot find `app` | The command was started outside `backend/`; rerun with `cd backend &&`. |
| `uv: command not found` | The default Bash environment does not expose the project toolchain; repair that environment before running checks. |
| `format.sh` reports `ruff: command not found` | Run the equivalent `uv run ruff` commands or update the script; do not add a global `ruff` solely to mask the wrapper's toolchain boundary. |

#### 5. Good / Base / Bad Cases

- Good: a Windows command uses the default `bash` and changes to `backend/`
  before calling `./scripts/lint.sh`.
- Base: a Linux or CI command changes to `backend/` before calling the same
  lint script.
- Bad: `bash backend/scripts/lint.sh` runs from the repository root, so mypy
  receives a nonexistent `app` path.

#### 6. Tests Required

- Before a Windows quality gate, verify `bash -lc 'uv --version'` succeeds.
- Run `lint.sh` from `backend/` and preserve its exit code in the handoff.
- When formatting is required, verify the explicit `uv run ruff` commands
  succeed until `format.sh` is made toolchain-aware.

#### 7. Wrong Vs Correct

#### Wrong

```powershell
bash backend/scripts/lint.sh
```

#### Correct

```powershell
bash -lc 'cd backend && ./scripts/lint.sh'
```

### Scenario: Isolated PostgreSQL Test Database

#### 1. Scope / Trigger

- Trigger: running any backend pytest suite, focused destructive test, or local
  API E2E flow that initializes or clears PostgreSQL data.

#### 2. Signatures

```bash
POSTGRES_DB=aiadmin_test bash scripts/test.sh
POSTGRES_DB=aiadmin_test uv run pytest tests/<path>
```

For local PowerShell runs from `backend/`, the ignored root `.env_test` may
provide the test environment without changing the current shell:

```powershell
uv run --env-file ../.env_test pytest tests/<path>
```

#### 3. Contracts

- `aiadmin_test` is the default local isolated PostgreSQL database for
  destructive backend tests and API E2E. A pre-created, non-production name
  ending in `_test` or `_pytest` is valid when a fresh or concurrent run must
  avoid session data left by earlier manual verification.
- The database must exist before pytest runs; the session fixture upgrades it
  to the Alembic head and clears its supported test tables after the suite. It
  does not clear them before setup, so a new safe database is the correct way
  to rule out residue without deleting another test run's records.
- `.env_test` is a developer-local environment file and must remain ignored;
  it must set `POSTGRES_DB` to `aiadmin_test` or another pre-created database
  name ending in `_test` or `_pytest`. CI and environments without this file
  must set `POSTGRES_DB` explicitly.
- `POSTGRES_DB=aiadmin` is development data and must never be used for tests.

#### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| `POSTGRES_DB=aiadmin_test` and the database exists | Run migrations and tests. |
| A clean or concurrent verification needs separate state | Create and select a pre-created name ending in `_test` or `_pytest`; do not clear another run's database. |
| Name is `aiadmin`, blank, or a system database | Refuse before destructive test setup. |
| Name has a safe suffix but the database does not exist | Fail during connection/migration; create the isolated database, never substitute the development database. |

#### 5. Good / Base / Bad Cases

- Good: a focused backend test exports `POSTGRES_DB=aiadmin_test` and leaves
  `aiadmin` untouched.
- Good: a local focused test runs `uv run --env-file ../.env_test pytest ...`
  from `backend/`, with `.env_test` ignored and `POSTGRES_DB=aiadmin_test`.
- Good: a full verification uses `aiadmin_clean_pytest` so session-scoped
  fixture data cannot be confused with another local E2E run.
- Base: the fixture clears its known tables after a successful suite.
- Bad: pointing pytest at `aiadmin` to avoid creating the test database.
- Bad: committing `.env_test` or relying on it in CI, where the local file is
  intentionally unavailable.

#### 6. Tests Required

- Verify the database guard rejects `aiadmin` before migrations run.
- Verify CI/local test commands set `POSTGRES_DB=aiadmin_test` before pytest.
- Verify `uv run --env-file ../.env_test python -c ...` exposes the safe
  `POSTGRES_DB` value before running a destructive test suite.

#### 7. Wrong Vs Correct

#### Wrong

```bash
POSTGRES_DB=aiadmin uv run pytest tests/core/test_config.py
```

#### Correct

```bash
POSTGRES_DB=aiadmin_test uv run pytest tests/core/test_config.py
```

For a local PowerShell shortcut, the equivalent is:

```powershell
uv run --env-file ../.env_test pytest tests/core/test_config.py
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

- Preserve the current hybrid architecture: lightweight CRUD stays lightweight, while operational workflows may own module-local boundaries.
- Use review pressure to stop regression back into thick routes, giant shared services, or pattern-driven ceremony.

---

## Code Anchors

- Service-first behavior: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Error baseline: [`backend/app/main.py`](../../../backend/app/main.py), [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Model/schema contract examples: [`backend/app/models/user.py`](../../../backend/app/models/user.py), [`backend/app/schemas/user.py`](../../../backend/app/schemas/user.py)
- Lightweight item CRUD: [`backend/app/api/routes/items.py`](../../../backend/app/api/routes/items.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py), [`backend/app/crud/item.py`](../../../backend/app/crud/item.py)
- Backend and cross-layer tooling: [`backend/pyproject.toml`](../../../backend/pyproject.toml), [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
