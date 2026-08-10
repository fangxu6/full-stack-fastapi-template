# State Management

> State boundaries for this repository's frontend.

---

## Overview

This repo intentionally avoids a separate global store. The practical state model is:

- local UI state in components
- server state in React Query
- route state in TanStack Router
- auth token persistence in `localStorage`
- generated OpenAPI services as the request boundary

---

## Current Reality

- Auth token persistence is wired through:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)
- Query state powers current-user and page data fetching:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Mutations invalidate query state through React Query:
  - [`frontend/src/platform/system/components/users/EditUserMenuItem.tsx`](../../../frontend/src/platform/system/components/users/EditUserMenuItem.tsx)
  - [`frontend/src/platform/system/components/users/DeleteUserMenuItem.tsx`](../../../frontend/src/platform/system/components/users/DeleteUserMenuItem.tsx)
- Navigation and access behavior derives from the current permission query and
  pure permission helpers:
  - [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts)
  - [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)

---

## State Rules

- Use local component state for view-local interactions such as dialog visibility.
- Use React Query for server data, mutation lifecycles, and invalidation.
- Use router guards for access control and redirect behavior.
- Keep auth token persistence in one clear place and treat it as part of the auth boundary, not a random utility concern.
- Do not introduce global state for data already owned by React Query, router
  state, focused hooks, or generated client calls.
- Keep the singleton `QueryClient` in
  [`frontend/src/app/query-client.ts`](../../../frontend/src/app/query-client.ts).
  `main.tsx` provides that instance to React, and non-React router guards use
  the same instance through an app-level access module.
- For permission data, define the query key, generated-client query function,
  and component freshness in
  [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts).
  React consumers use `useQuery(myPermissionsQueryOptions)`; route guards use
  `readMyPermissionsForRoute()`, which calls `fetchQuery` with `staleTime: 0`
  so every protected navigation reads fresh permissions while populating the
  shared cache.
- Keep permission predicates and types in
  [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
  pure. Do not move API/query orchestration there.

## Query Retry Policy

- Configure shared query retries only through the `QueryClient` in
  `frontend/src/app/query-client.ts`; per-query `retry: false` remains authoritative and
  mutations retain their default no-retry behavior.
- Retry only `GET`, `HEAD`, and `OPTIONS` requests when Axios reports a
  response-less network failure or the response status is `408`, `429`, or
  `5xx`. Never retry cancelled, aborted, unknown-method, or write requests.
- Use delays of 1 second then 2 seconds. A `429` may override the delay with a
  delta-seconds or HTTP-date `Retry-After` value between 0 and 30 seconds;
  invalid, past, missing, or over-limit values use the normal delay.
- Keep `Retry-After` handling in `app/query-retry.ts`. The generated
  `ApiError` omits response headers, so the app-owned OpenAPI response
  interceptor exposes only `429` header data without editing generated files.
- Do not introduce a global request timeout. Direct browser downloads remain
  outside this policy.

### Tests Required

- Unit-test retryable statuses, safe-method enforcement, cancellation, retry
  count, and both `Retry-After` formats in
  `frontend/src/app/query-retry.test.ts`.

---

## Recommended Direction

- Avoid introducing a separate global state library unless repeated cross-route state truly cannot be modeled with query state, router state, or focused hooks.
- Keep navigation and page access derived from the permission query in
  [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts)
  and `PermissionCode`/`hasPermission` in
  [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts),
  rather than duplicated booleans or ad hoc user flags spread across pages.
- Preserve the current `401/403` handling pattern in
  [`frontend/src/app/query-client.ts`](../../../frontend/src/app/query-client.ts)
  and permission error classification in
  [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts)
  unless there is a deliberate redesign.

---

## Regression Checks

- If auth behavior changes, verify token persistence, logout clearing, and redirect behavior.
- If route-access behavior changes, verify both route guards and menu visibility.
- If mutations change a list page, verify the relevant query invalidation path still exists.
- If generated client services or response types change, verify server-state
  consumers compile against regenerated types.

---

## Code Anchors

- Auth state and token persistence: [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts), [`frontend/src/main.tsx`](../../../frontend/src/main.tsx)
- Shared query client and permission access: [`frontend/src/app/query-client.ts`](../../../frontend/src/app/query-client.ts), [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts)
- Navigation derived from the permission query: [`frontend/src/app/permissions.ts`](../../../frontend/src/app/permissions.ts), [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
- Permission entrypoint: [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
- Server-state consumers: [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx), [`frontend/src/platform/system/components/users/EditUserMenuItem.tsx`](../../../frontend/src/platform/system/components/users/EditUserMenuItem.tsx)
