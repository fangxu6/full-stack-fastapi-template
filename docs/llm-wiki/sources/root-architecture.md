---
title: Root architecture source
created: 2026-06-04
updated: 2026-06-04
type: source
tags:
  - llm-wiki
  - architecture
status: active
source_count: 1
---

# Root Architecture Source

## Source

- Path: `ARCHITECTURE.md`
- Role: Top-level repository architecture and documentation entrypoint.

## Key Facts

- The repository contains a FastAPI backend, React frontend, shared docs, scripts, and Docker Compose orchestration.
- The target stack is FastAPI, SQLModel, PostgreSQL, React, TypeScript, TanStack Router, TanStack Query, generated OpenAPI client, Docker Compose, and Traefik.
- The repository is transitioning from a generic template into an enterprise scaffold with clearer platform boundaries.
- Backend owns authentication, authorization, business rules, persistence, transaction boundaries, error responses, and server-side observability.
- Frontend owns page composition, routes, guards, UI states, interaction flows, and generated-client API calls.

## Durable Guidance

- New work should choose target layers before editing.
- Frontend route files should remain thin.
- Backend work should reuse shared exception handling.
- Documentation should stay aligned when boundaries change.

## Related Pages

- [[docs/llm-wiki/entities/full-stack-fastapi-template|full-stack-fastapi-template]]
- [[docs/llm-wiki/entities/fastapi-backend|FastAPI backend]]
- [[docs/llm-wiki/entities/react-frontend|React frontend]]
- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]

