# Frontend Development Guidelines

> Actual conventions for this repository's React + Vite frontend.

---

## Overview

The frontend is a React 19 + TypeScript + Vite application under `frontend/`, using TanStack Router, TanStack Query, Tailwind CSS, Radix UI, and Biome.

Use this index as the frontend entry point for local Trellis guidance. The root `AGENTS.md` no longer carries frontend operational detail; frontend-specific commands and guardrails live here.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | In progress |
| [Component Guidelines](./component-guidelines.md) | Component patterns, props, composition | In progress |
| [Hook Guidelines](./hook-guidelines.md) | Custom hooks, data fetching patterns | In progress |
| [State Management](./state-management.md) | Local state, global state, server state | In progress |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, forbidden patterns | Customized |
| [Type Safety](./type-safety.md) | Type patterns, validation | In progress |

---

## Read Order

1. Start with [Directory Structure](./directory-structure.md) before placing files.
2. Read [Component Guidelines](./component-guidelines.md) before editing components or routes.
3. Read [Hook Guidelines](./hook-guidelines.md) and [State Management](./state-management.md) before adding hooks or shared state.
4. Use [Type Safety](./type-safety.md) and [Quality Guidelines](./quality-guidelines.md) as the implementation checklist.

---

## Local Dev Defaults

- Install deps from `frontend/`: `bun install`
- Dev server from `frontend/`: `bun run dev`
- Build from `frontend/`: `bun run build`
- Lint from `frontend/`: `bun run lint`
- Playwright from `frontend/`: `bunx playwright test`
- Single Playwright test: `bunx playwright test tests/login.spec.ts`

Assume frontend local verification uses `http://127.0.0.1:5173` unless the task explicitly says otherwise.

---

## Scope Notes

- Main frontend code lives under `frontend/src/**`.
- Shared folders include `app`, `components`, `features`, `hooks`, `lib`, `platform`, `routes`, and `shared`.
- Generated or framework-owned files should not be edited directly:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`
  - `frontend/src/components/ui/**`

---

## Skill and Rule Hooks

- Regular Python-free React work should prefer repo-local React guidance first, then use `vercel-react-best-practices` only when its performance rules are relevant.
- Prefer `type` imports and `@/` aliases in app code.
- Biome enforces double quotes and semicolons-as-needed behavior for this frontend.

---

## Integration Notes

- When backend API schemas change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Keep diffs focused; avoid mass formatting or edits to generated client code.
