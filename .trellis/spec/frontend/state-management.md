# State Management

> State boundaries for this repository's frontend.

---

## Overview

This repo intentionally avoids a separate global store. The practical state model is:

- local UI state in components
- server state in React Query
- route state in TanStack Router
- auth token persistence in `localStorage`

---

## Current Reality

- Auth token persistence is wired through:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)
- Query state powers current-user and page data fetching:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Navigation and access behavior derives from user state and permission helpers:
  - [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)

---

## State Rules

- Use local component state for view-local interactions such as dialog visibility.
- Use React Query for server data, mutation lifecycles, and invalidation.
- Use router guards for access control and redirect behavior.
- Keep auth token persistence in one clear place and treat it as part of the auth boundary, not a random utility concern.

---

## Recommended Direction

- Avoid introducing a separate global state library unless repeated cross-route state truly cannot be modeled with query state, router state, or focused hooks.
- Keep admin navigation and permission behavior derived from current-user data rather than duplicated booleans spread across pages.
- Preserve the current `401/403` handling pattern in [`frontend/src/main.tsx`](../../../frontend/src/main.tsx) unless there is a deliberate redesign.

---

## Regression Checks

- If auth behavior changes, verify token persistence, logout clearing, and redirect behavior.
- If route-access behavior changes, verify both route guards and menu visibility.
- If mutations change a list page, verify the relevant query invalidation path still exists.

---

## Code Anchors

- Auth state and token persistence: [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts), [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)
- Navigation derived from user state: [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
- Permission entrypoint: [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
