# Directory Structure

> Frontend file-placement rules for this repository.

---

## Overview

The frontend structure is no longer a loose collection of routes and components. It has an intended layered boundary model, and future changes should preserve it aggressively.

---

## Current Reality

```text
frontend/src/
├── app/
├── client/
├── features/
├── platform/
├── routes/
└── shared/
```

- `routes/*` already acts mostly as route entry wiring:
  - [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx)
  - [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
  - [`frontend/src/routes/_layout/admin.tsx`](../../../frontend/src/routes/_layout/admin.tsx)
- `app/*` owns shell and navigation concerns:
  - [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx)
  - [`frontend/src/app/navigation/AppSidebar.tsx`](../../../frontend/src/app/navigation/AppSidebar.tsx)
  - [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- `platform/*` owns cross-business application areas such as auth and system:
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
  - [`frontend/src/platform/system/pages/AdminUsersPage.tsx`](../../../frontend/src/platform/system/pages/AdminUsersPage.tsx)
- `features/*` owns business feature slices:
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- `shared/*` owns reusable feedback, table, layout, theme, hooks, utilities,
  and permission helpers:
  - [`frontend/src/shared/components/feedback/ErrorState.tsx`](../../../frontend/src/shared/components/feedback/ErrorState.tsx)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
- `client/*`, `routeTree.gen.ts`, and `shared/components/ui/*` are generated or
  vendor-style surfaces for normal feature work:
  - [`frontend/src/client/types.gen.ts`](../../../frontend/src/client/types.gen.ts)
  - [`frontend/src/routeTree.gen.ts`](../../../frontend/src/routeTree.gen.ts)
  - [`frontend/src/shared/components/ui/button.tsx`](../../../frontend/src/shared/components/ui/button.tsx)

---

## Layer Ownership Rules

- `routes/*`: route declarations, `beforeLoad`, metadata, and page entry imports only.
- `app/*`: global shell, app layout, menu config, router guards, and other application-frame concerns.
- `platform/*`: reusable platform subsystems such as auth, docs, or system administration.
- `features/*`: feature-specific business domains.
- `shared/*`: only code that is truly reusable across domains without carrying business-page assumptions.

---

## Strong Constraints

- Do not build full pages directly inside `routes/*.tsx`.
- Do not use `shared/*` as the default destination for code that only one platform domain or feature needs.
- Keep navigation logic centralized in `app/navigation/*`.
- Keep route protection centralized in `app/router/guards.ts`.
- Keep permission-entry helpers centralized in `shared/permissions/*`.
- Do not manually edit generated route tree or OpenAPI client output unless the
  task is specifically about generation output.

---

## Current Reality vs Recommended Direction

### Current reality

- The repo already follows thin-route placement in multiple places.
- Auth and admin behavior already show the intended boundary split.

### Recommended direction

- Treat `app/platform/features/shared` as a hard architecture rail for new code.
- Continue moving any lingering page logic out of routes if new touchpoints expose thicker route files.

---

## Code Anchors

- Thin routes: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx), [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
- App shell and guards: [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx), [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- Platform and feature pages: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Generated boundaries: [`frontend/src/client/types.gen.ts`](../../../frontend/src/client/types.gen.ts), [`frontend/src/routeTree.gen.ts`](../../../frontend/src/routeTree.gen.ts)
