# Frontend Development Guidelines

> Repo-specific guidance for the React + Vite frontend in `frontend/src/**`.

---

## Overview

This frontend is also in a platform-batch-0 transition away from template-era file placement. The target layering is already visible in code and should now be treated as a strong constraint:

- `app/*` for shell, navigation, router guards
- `platform/*` for platform capabilities such as auth and system
- `features/*` for business features such as items
- `shared/*` for truly reusable UI, hooks, utils, and permission helpers
- `routes/*` as thin route-entry files

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Frontend layer ownership and thin-route rules | Customized |
| [Component Guidelines](./component-guidelines.md) | Shared-vs-domain component placement rules | Customized |
| [Hook Guidelines](./hook-guidelines.md) | Auth, server-state, and hook-boundary rules | Customized |
| [State Management](./state-management.md) | Query state, auth persistence, and route-driven state | Customized |
| [Quality Guidelines](./quality-guidelines.md) | Review guardrails, generated-file rules, regression checks | Customized |
| [Type Safety](./type-safety.md) | Generated client usage, Zod, alias rules | Customized |

---

## Read Order

1. Read [Directory Structure](./directory-structure.md) before placing files.
2. Read [Component Guidelines](./component-guidelines.md) before moving code into `shared/*` or building new page components.
3. Read [Hook Guidelines](./hook-guidelines.md) and [State Management](./state-management.md) before changing auth, query, or route-driven state.
4. Use [Type Safety](./type-safety.md) and [Quality Guidelines](./quality-guidelines.md) as the final review checklist.

---

## Current Reality

- Thin routes already exist and mostly delegate to page modules:
  - [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx)
  - [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
- App shell and navigation are already centralized:
  - [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx)
  - [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
- Route protection and permission entrypoints are already separated:
  - [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
- Auth token persistence and current-user query behavior are already coupled through:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)

---

## Recommended Direction

- Keep new route files thin. Do not move full page implementation back into `routes/*`.
- Put new cross-business capabilities under `platform/*` and new business workflows under `features/*`.
- Only promote code into `shared/*` once it is genuinely cross-domain and not page-specific.
- Continue using the generated OpenAPI client rather than inventing parallel hand-written request types.

---

## Local Dev Defaults

- Install deps from `frontend/`: `bun install`
- Dev server from `frontend/`: `bun run dev`
- Build from `frontend/`: `bun run build`
- Lint from `frontend/`: `bun run lint`
- Playwright from `frontend/`: `bunx playwright test`

Assume local frontend verification uses `http://127.0.0.1:5173` unless the task says otherwise.

---

## Cross-Layer Reminder

- When backend API schemas change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Frontend changes that affect routes, permissions, or error surfaces should preserve the current app-shell and guard structure.

---

## Code Anchors

- Thin route examples: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx), [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
- App-shell boundaries: [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx), [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- Page placement examples: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
