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
| [Pagination Contract](./pagination-contract.md) | Ant Design server-side pagination, API mapping, query state, and regressions | Customized |
| [Route Permission Navigation Contract](./route-permission-navigation-contract.md) | Route, guard, menu, and page-placement synchronization contract | Customized |
| [State Management](./state-management.md) | Query state, auth persistence, and route-driven state | Customized |
| [Quality Guidelines](./quality-guidelines.md) | Review guardrails, generated-file rules, regression checks | Customized |
| [Type Safety](./type-safety.md) | Generated client usage, Zod, alias rules | Customized |

---

## Read Order

1. Read [Directory Structure](./directory-structure.md) before placing files.
2. Read [Component Guidelines](./component-guidelines.md) before moving code into `shared/*` or building new page components.
3. Read [Route Permission Navigation Contract](./route-permission-navigation-contract.md) when adding pages, changing route guards, changing menu visibility, or moving page boundaries.
4. Read [Pagination Contract](./pagination-contract.md) before adding a server-paginated list or Ant Design Table pagination.
5. Read [Hook Guidelines](./hook-guidelines.md) and [State Management](./state-management.md) before changing auth, query, or route-driven state.
6. Use [Type Safety](./type-safety.md) and [Quality Guidelines](./quality-guidelines.md) as the final review checklist.

### Trigger-Based Routing

| Trigger | Required Reads |
| --- | --- |
| New page or page move | [Directory Structure](./directory-structure.md), [Component Guidelines](./component-guidelines.md), [Route Permission Navigation Contract](./route-permission-navigation-contract.md) |
| Route guard, menu, or permission change | [Route Permission Navigation Contract](./route-permission-navigation-contract.md), [State Management](./state-management.md), [Quality Guidelines](./quality-guidelines.md) |
| Auth, current-user, logout, or token behavior | [Hook Guidelines](./hook-guidelines.md), [State Management](./state-management.md), [Route Permission Navigation Contract](./route-permission-navigation-contract.md) |
| Generated client or API consumer change | [Type Safety](./type-safety.md), [State Management](./state-management.md), [../guides/cross-layer-thinking-guide.md](../guides/cross-layer-thinking-guide.md) |
| Server-paginated list or Ant Design Table pagination | [Pagination Contract](./pagination-contract.md), [Component Guidelines](./component-guidelines.md), [State Management](./state-management.md), [Quality Guidelines](./quality-guidelines.md) |
| Shared component/helper extraction | [Component Guidelines](./component-guidelines.md), [../guides/code-reuse-thinking-guide.md](../guides/code-reuse-thinking-guide.md) |
| Ant Design component adoption | [Component Guidelines](./component-guidelines.md), [Quality Guidelines](./quality-guidelines.md) |

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
- Treat route access, menu visibility, permission helpers, and page placement as one linked contract rather than four independent edits.

---

## Local Dev Defaults

- Install deps from `frontend/`: `bun install`
- Dev server from `frontend/`: `bun run dev`
- Build from `frontend/`: `bun run build`
- Lint from `frontend/`: `bun run lint` (this runs Biome with `--write --unsafe`; always review the resulting diff)
- Playwright from `frontend/`: `bunx playwright test`
- Client generation from repo root after backend contract changes: `bash ./scripts/generate-client.sh`
- Current configured stack includes React 19, Vite 8, TanStack Router 1.170,
  React Query 5.101, Tailwind 4, Biome 2.4, Playwright 1.61, and `@hey-api/openapi-ts`
  in [`frontend/package.json`](../../../frontend/package.json).
- Vite owns the `@/` alias, TanStack Router plugin, React SWC plugin, and
  Tailwind plugin in [`frontend/vite.config.ts`](../../../frontend/vite.config.ts).
- Biome excludes generated/vendor-style paths such as `src/client/**`,
  `src/routeTree.gen.ts`, and `src/components/ui/**` in
  [`frontend/biome.json`](../../../frontend/biome.json).

Assume local frontend verification uses `http://127.0.0.1:5173` unless the task says otherwise.

---

## Cross-Layer Reminder

- When backend API schemas change, regenerate the frontend client with `bash ./scripts/generate-client.sh`.
- Frontend changes that affect routes, permissions, or error surfaces should preserve the current app-shell and guard structure.
- Do not manually patch generated client files to match backend changes.

## Trigger Reminder

Read [Route Permission Navigation Contract](./route-permission-navigation-contract.md) before changing any of:

- new pages
- protected routes
- menu items
- `app/router/guards.ts`
- `shared/permissions/*`
- page moves between `routes/*`, `platform/*`, and `features/*`

---

## Code Anchors

- Thin route examples: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx), [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
- App-shell boundaries: [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx), [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- Page placement examples: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Tooling: [`frontend/package.json`](../../../frontend/package.json), [`frontend/biome.json`](../../../frontend/biome.json), [`frontend/vite.config.ts`](../../../frontend/vite.config.ts)
