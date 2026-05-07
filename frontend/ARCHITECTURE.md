# Frontend Architecture

This document describes the current frontend architecture after the Enterprise Scaffold batch-0 boundary migration.

## 1. Current Structure

```text
frontend/src/
├── app/                            # Application shell and top-level wiring
│   ├── layout/                     # AppLayout, AppHeader, AppFooter
│   ├── navigation/                 # Sidebar, menu config, navigation types
│   └── router/                     # Route guards
├── client/                         # Generated OpenAPI client
├── components/ui/                  # Shared design-system primitives (generated/vendor-style layer)
├── features/                       # Business features
│   └── items/
│       ├── components/
│       └── pages/
├── hooks/                          # Existing app-level hooks
├── platform/                       # Cross-business platform capabilities
│   ├── auth/
│   │   ├── components/
│   │   ├── pages/
│   │   └── index.ts
│   ├── docs/
│   └── system/
│       ├── components/users/
│       ├── pages/
│       └── index.ts
├── routes/                         # Thin route files
├── shared/                         # Cross-domain shared capabilities
│   ├── components/
│   │   ├── branding/
│   │   ├── feedback/
│   │   ├── layout/
│   │   ├── table/
│   │   └── theme/
│   ├── hooks/
│   ├── permissions/
│   └── utils/
└── main.tsx
```

## 2. Layer Responsibilities

### `app/*`

Owns application-wide concerns:

- app shell layout
- sidebar and navigation composition
- route guards
- top-level UI framing

This layer should not absorb feature-specific business behavior.

### `platform/*`

Owns platform capabilities that are broader than a single business feature:

- authentication pages/components
- user settings
- admin/system management
- internal docs/rules experience

### `features/*`

Owns concrete business features. Right now the main real example is:

- `features/items/*`

Future business domains should prefer this layer over adding more route-local page implementations.

### `shared/*`

Owns truly reusable cross-domain pieces:

- shared UI
- reusable feedback states
- shared table/layout/theme wrappers
- permissions helpers
- generic utilities

Only promote code into `shared/*` once it is genuinely cross-domain and not tied to a page flow.

## 3. Route Architecture

The repository is moving away from “route file contains full page implementation”.

### Current rule

- `routes/*` should be thin
- route files define:
  - route registration
  - guard wiring
  - metadata
  - import of the real page component

### Real examples

- `routes/login.tsx` -> `platform/auth/pages/LoginPage.tsx`
- `routes/_layout.tsx` -> `app/layout/AppLayout.tsx`
- `routes/_layout/items.tsx` -> `features/items/pages/ItemsPage.tsx`
- `routes/_layout/admin.tsx` -> `platform/system/pages/AdminUsersPage.tsx`

## 4. Navigation and Permission Boundary

The batch-0 migration centralized navigation concerns.

### Current placement

- sidebar implementation: `app/navigation/*`
- route guards: `app/router/guards.ts`
- menu permission checks: `shared/permissions/*`

### Why this matters

This prevents permission checks from being reimplemented ad hoc in pages and keeps navigation policy in one place.

Right now the admin menu rule is still minimal (`is_superuser`), but the boundary is ready for broader RBAC later.

## 5. Shared Component Strategy

The repository has moved away from the old flat `components/Common/*` pattern.

### Preferred import style

Use grouped shared entrypoints such as:

- `@/shared/components/branding`
- `@/shared/components/feedback`
- `@/shared/components/layout`
- `@/shared/components/table`
- `@/shared/components/theme`

The top-level `shared/components/index.ts` is a namespace aggregator, not a signal to flatten all imports again.

### What should stay out of `shared/*`

- feature-specific modal orchestration
- auth-only page composition
- admin-only table logic
- components coupled to one route family

Those belong under `platform/*` or `features/*`.

## 6. Data and State Flow

### Main data sources

- generated OpenAPI client in `client/*`
- auth state helpers in `hooks/useAuth.ts`
- TanStack Router for navigation/guards
- TanStack Query for request orchestration and caching

### Typical flow

```text
Route
  -> Page module
  -> page/domain components
  -> hooks / client
  -> backend API
```

## 7. Transitional Reality

This frontend architecture is intentionally in a hybrid state:

- the new boundaries are real and in use
- some existing hooks and UI primitives still live in legacy-friendly locations
- not every page family has been migrated yet

That means new code should follow the target boundary, not the old shortcut.

## 8. Growth Rules

When adding new frontend work:

1. decide whether it belongs to `platform` or `features`
2. put page implementations in `pages/`
3. keep route files thin
4. keep app-wide chrome in `app/*`
5. only move code into `shared/*` when it is actually reusable across domains

Avoid:

- rebuilding `components/Common/*`
- putting full pages back into `routes/*`
- scattering permission logic across page components
