# Hook Guidelines

> Hook boundaries and auth/query patterns for this repository.

---

## Overview

Hooks in this repo should stay focused. The most important current hook is `useAuth`, because it ties together token persistence, current-user query state, navigation, and mutation flows.

---

## Current Reality

- Auth token presence is checked through `localStorage`:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
- `useAuth` owns current-user query wiring plus login/logout/signup behavior:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
- Route guards use thin helper entrypoints rather than embedding all auth logic directly in route files:
  - [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- Page-specific query helpers often stay inside the page file:
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)

---

## Hook Rules

- Keep hooks focused on one concern.
- Use hooks for reusable browser/react behavior, auth wiring, or repeated page interaction patterns.
- Do not move every page-local query into a hook if a local helper inside the page remains clearer.
- Keep auth-routing logic split cleanly:
  - token presence and user query behavior in `useAuth`
  - route redirects and route-entry protection in `app/router/guards.ts`

---

## Recommended Direction

- Continue letting `useAuth` be the main auth hook until there is a clear reason to split it.
- If auth complexity grows, extract smaller auth helpers without dissolving the current guard boundary.
- Keep permission checks centralized through shared helpers rather than scattering role logic through arbitrary hooks or pages.

---

## Common Mistakes

- Duplicating token or current-user logic outside `useAuth` without a good boundary reason.
- Moving thin route-guard responsibilities into route components or page components.
- Extracting page-local query logic into hooks too early, which can hide ownership instead of clarifying it.

---

## Code Anchors

- Auth hook: [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
- Route guards: [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
- Page-local query pattern: [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
