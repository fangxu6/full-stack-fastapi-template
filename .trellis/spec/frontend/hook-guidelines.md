# Hook Guidelines

> How hooks are used in this project.

---

## Overview

Custom hooks live under `frontend/src/hooks/**` and use the standard `use*` naming convention. The project uses hooks for auth state, browser/device helpers, and toast helpers, while page-level server data often stays directly inside route or feature components through React Query.

---

## Custom Hook Patterns

- Keep hooks focused on one concern, such as authentication (`useAuth`), viewport detection (`useIsMobile`), clipboard behavior, or toast behavior.
- Hooks can return mutation objects directly when that keeps feature components simple, as shown in [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts).
- Keep browser-only effects encapsulated inside hooks, for example `window.matchMedia` usage in [`frontend/src/hooks/useMobile.ts`](../../../frontend/src/hooks/useMobile.ts).

---

## Data Fetching

- React Query is the default server-state mechanism.
- Page components often define local `get...QueryOptions()` helpers and consume them with `useSuspenseQuery`, as seen in `ItemsPage` and `AdminUsersPage`.
- Mutations use `useMutation` plus `queryClient.invalidateQueries(...)` to refresh related lists.
- Shared auth guard behavior can also call API client methods directly in route guards, as shown in [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts).

---

## Naming Conventions

- Hook files and exports should start with `use`, for example `useAuth`, `useCustomToast`, and `useIsMobile`.
- For hooks that expose a single concern, default export is acceptable and already common in the repo.
- Avoid hiding non-hook utilities inside hook files; keep pure helpers in shared utility modules when they do not need React state/effects.

---

## Common Mistakes

- Moving simple one-page query logic into a hook too early when a page-local query helper is clearer.
- Forgetting to invalidate affected React Query keys after mutations.
- Mixing browser APIs into components repeatedly instead of encapsulating them once in a hook.
