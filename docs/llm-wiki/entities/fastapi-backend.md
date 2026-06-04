---
title: FastAPI backend
created: 2026-06-04
updated: 2026-06-04
type: entity
tags:
  - llm-wiki
  - backend
  - fastapi
status: active
---

# FastAPI Backend

## Summary

The backend is a FastAPI application under `backend/app` using SQLModel, PostgreSQL, shared security helpers, centralized dependencies, and unified request/error handling.

## Target Boundaries

- `api/*`: HTTP transport and router aggregation.
- `api/dependencies/*`: reusable request-scoped dependencies.
- `services/*`: business orchestration.
- `crud/*`: atomic persistence access.
- `models/*`: ORM entities only.
- `schemas/*`: API DTOs only.
- `core/*`: cross-cutting platform capabilities.
- `infra/*`: infrastructure boundary.
- `modules/*`: future domain/module boundary.

## Durable Rules

- Use shared exception handling and request ID behavior.
- Keep business rules out of route handlers when practical.
- Reuse auth/db dependencies instead of reimplementing them.
- Add backend tests around success, auth, validation, and error paths for new capabilities.

## Sources

- [[docs/llm-wiki/sources/backend-architecture|Backend architecture source]]
- [[docs/llm-wiki/sources/private-knowledge-architecture|Private knowledge architecture source]]

