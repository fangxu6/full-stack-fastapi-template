# State Management

> How state is managed in this project.

---

## Overview

This frontend does not use a separate global store library. State is split across local React state, server state in React Query, route state in TanStack Router, and browser persistence such as `localStorage` for auth tokens.

---

## State Categories

- Local UI state: `useState` inside components for dialogs, menus, and form visibility, for example `isOpen` in `AddItemDialog`.
- Server state: React Query for lists, current user data, and mutation lifecycles.
- Route state: TanStack Router file routes and route guards control page access and layout nesting.
- Browser persistence: `localStorage` currently stores `access_token` and is checked by auth helpers in [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts).

---

## When to Use Global State

- Prefer not to introduce a new global store unless repeated cross-route state cannot be expressed with React Query, router state, or small focused hooks.
- Shared auth and permission checks currently derive from the current user query plus token presence, not from a separate app-wide store.
- Navigation behavior that depends on the current user should stay derived from current-user data, as shown in [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts).

---

## Server State

- Create query option helpers close to the page or feature using them.
- Use query keys like `["items"]`, `["users"]`, and `["currentUser"]`.
- Invalidate affected queries on mutation settle/success.
- Let the root app wire shared React Query behavior, including auth-failure handling, in [`frontend/src/main.tsx`](../../../frontend/src/main.tsx).

---

## Common Mistakes

- Promoting state to app-wide scope when a page-local `useState` or `useSuspenseQuery` would be simpler.
- Forgetting that auth state depends on both token persistence and current-user query freshness.
- Duplicating server data in local component state instead of deriving it from the query result.
