# Directory Structure

> How frontend code is organized in this project.

---

## Overview

Frontend code lives under `frontend/src` and is split by role: app shell, routes, feature modules, platform-specific areas, shared utilities, and reusable UI primitives.

---

## Directory Layout

```text
frontend/src/
├── app/
│   ├── layout/
│   ├── navigation/
│   └── router/
├── client/
├── components/
│   ├── theme-provider.tsx
│   └── ui/
├── features/
│   └── items/
├── hooks/
├── platform/
│   ├── auth/
│   ├── docs/
│   └── system/
├── routes/
├── shared/
│   ├── components/
│   ├── hooks/
│   ├── permissions/
│   └── utils/
├── index.css
└── main.tsx
```

---

## Module Organization

- File-based routes live in `src/routes/**` and should mostly wire route metadata, route guards, and page entrypoints.
- App shell, layout chrome, and navigation live under `src/app/**`.
- User-facing feature code should prefer `src/features/**` when it belongs to a business area such as items.
- Cross-cutting product areas that feel more like application subsystems can live under `src/platform/**`, for example auth, docs, and system pages.
- Shared reusable view helpers, feedback states, tables, and permission helpers belong under `src/shared/**`.
- Generated API client code lives in `src/client/**` and should only change through regeneration.

---

## Naming Conventions

- Use PascalCase for React component files such as `AppLayout.tsx`, `ItemsPage.tsx`, and `AddItemDialog.tsx`.
- Use lowercase route filenames that match route intent, such as `login.tsx`, `_layout.tsx`, and `_layout/items.tsx`.
- Hook files use `use*` naming, for example `useAuth.ts` and `useCustomToast.ts`.
- Prefer descriptive folder names by role or feature instead of generic buckets like `misc`.

---

## Examples

- Root app bootstrap: [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)
- Layout shell: [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx)
- Route entrypoint: [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx)
- Feature page: [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Shared permission helper: [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
