---
title: React frontend
created: 2026-06-04
updated: 2026-06-04
type: entity
tags:
  - llm-wiki
  - frontend
  - react
status: active
---

# React Frontend

## Summary

The frontend is a React + Vite + TypeScript application under `frontend/src`, using TanStack Router, TanStack Query, generated OpenAPI client code, Tailwind, and shadcn/ui.

## Target Boundaries

- `app/*`: shell, navigation, route guards, and top-level wiring.
- `platform/*`: cross-business capabilities such as auth, system admin, and internal docs.
- `features/*`: concrete business features.
- `shared/*`: reusable cross-domain components, hooks, permissions, and utilities.
- `routes/*`: thin route declarations only.

## Durable Rules

- Do not put full page implementations back into route files.
- Prefer `platform/*/pages` or `features/*/pages` for real page logic.
- Promote code into `shared/*` only when it is genuinely cross-domain.
- Keep navigation and permission logic centralized.

## Sources

- [[docs/llm-wiki/sources/frontend-architecture|Frontend architecture source]]
- [[docs/llm-wiki/sources/private-knowledge-architecture|Private knowledge architecture source]]

