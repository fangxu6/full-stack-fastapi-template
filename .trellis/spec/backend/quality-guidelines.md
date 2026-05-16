# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

Backend work in this repo must stay type-safe, layered, and narrowly scoped. Prefer small changes that align with the existing FastAPI + SQLModel structure instead of introducing parallel patterns.

---

## Forbidden Patterns

- Do not modify `.env` files or secrets as part of normal task work.
- Do not use `print`; use logging when output is needed.
- Do not bypass the service layer by putting business orchestration straight into route handlers.
- Do not make unrelated mass-formatting changes while touching backend files.
- Do not forget frontend client regeneration when an API schema change affects generated client code.

---

## Required Patterns

- Type hints everywhere; backend mypy runs in strict mode.
- Use `model_validate` / `model_dump` and `sqlmodel_update` patterns where partial update flows already rely on them.
- Raise `HTTPException` with explicit `status_code` and `detail`.
- Keep layering explicit: `api -> services -> crud -> models/schemas`.
- Activate `python-patterns` before Python implementation, refactor, or review work.

---

## Testing Requirements

- Prefer the smallest meaningful verification step for the change: local pytest, docker test flow, or targeted running-stack tests.
- If a change touches API contract shape, verify whether generated frontend client impact exists.
- If tests are skipped, call that out explicitly in the final handoff.

---

## Code Review Checklist

- Is the change limited to the intended backend slice?
- Are types explicit and consistent with current backend patterns?
- Is business logic placed in services instead of routes?
- Are error responses clear and intentional?
- If API schema changed, was client regeneration handled?
