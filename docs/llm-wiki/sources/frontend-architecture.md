---
title: Frontend architecture source
created: 2026-06-04
updated: 2026-06-04
type: source
tags:
  - llm-wiki
  - frontend
  - architecture
status: active
source_count: 1
---

# Frontend Architecture Source

## Source

- Path: `frontend/ARCHITECTURE.md`
- Role: Frontend layering, route strategy, navigation, permissions, shared components, and state flow.

## Key Facts

- Frontend code lives under `frontend/src`.
- Target layers are `app`, `platform`, `features`, `shared`, and thin `routes`.
- `app/*` owns shell, navigation, guards, and top-level UI framing.
- `platform/*` owns cross-business capabilities such as auth, admin/system, and internal docs.
- `features/*` owns concrete business features such as items.
- `shared/*` owns genuinely reusable cross-domain components, hooks, permissions helpers, and utilities.
- Generated OpenAPI client and TanStack Query are the primary backend data access path.

## Durable Guidance

- Keep route files thin.
- Place page implementations under `platform/*/pages` or `features/*/pages`.
- Avoid rebuilding flat `components/Common/*`.
- Keep permission logic centralized through app/router and shared permissions boundaries.

## Related Pages

- [[docs/llm-wiki/entities/react-frontend|React frontend]]
- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]

