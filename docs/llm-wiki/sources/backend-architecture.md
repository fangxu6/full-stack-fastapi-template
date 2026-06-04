---
title: Backend architecture source
created: 2026-06-04
updated: 2026-06-04
type: source
tags:
  - llm-wiki
  - backend
  - architecture
status: active
source_count: 1
---

# Backend Architecture Source

## Source

- Path: `backend/ARCHITECTURE.md`
- Role: Backend boundary, request flow, error handling, and module-growth guidance.

## Key Facts

- Backend code lives under `backend/app`.
- Target layers are `api`, `services`, `crud`, `models`, `schemas`, `core`, `infra`, and `modules`.
- `app/core/exceptions.py` centralizes request IDs, application errors, HTTP exceptions, validation errors, and unhandled error handling.
- Error responses should converge on `{ "detail": "...", "request_id": "..." }`.
- `models/*` should export ORM entities only, while `schemas/*` should export API DTOs only.
- `modules/*` and `infra/*` exist as forward-looking boundaries and are not yet fully migrated.

## Durable Guidance

- Keep business rules out of route handlers when adding backend behavior.
- Reuse request-scoped dependencies from `api/dependencies/*`.
- Do not bypass shared error handling or request tracing.
- Add tests for success, auth, validation, and not-found/error paths when adding backend capability.

## Related Pages

- [[docs/llm-wiki/entities/fastapi-backend|FastAPI backend]]
- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]

