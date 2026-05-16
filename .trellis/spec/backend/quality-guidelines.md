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

- Keep layering explicit: `api -> services -> crud -> models/schemas`.
- Use semantic application exceptions for expected business failures.
- Keep new platform-wide behavior in `core/*`.
- Keep model/schema changes paired with migration thinking and frontend client impact review.
- Use explicit typing and current SQLModel update/validation patterns.

---

## Strong Review Rules

- New module work should attach to the existing platform skeleton rather than expanding one large shared file forever.
- If a feature suggests a bounded business slice, prefer a deliberate path through `modules/*` over uncontrolled growth in route files or a giant `crud.py`.
- API contract changes require checking whether `bash ./scripts/generate-client.sh` must be run.
- New or changed error branches should preserve the `detail + request_id` response contract.

---

## Minimum Validation Expectations

- If a backend change affects error behavior, verify at least one path that exercises the unified error shape.
- If auth, permission, or validation behavior changes, verify the relevant `401`, `403`, or `422` contract path.
- If request/response models change, review frontend generated-client impact before closing the task.
- If tests are skipped, say so explicitly in the handoff.

---

## Forbidden Patterns

- Thick route handlers with business orchestration
- New ad hoc error payload shapes
- Model or schema changes without migration review
- Backend contract changes that ignore frontend SDK regeneration needs
- Unrelated mass formatting while touching backend files

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
