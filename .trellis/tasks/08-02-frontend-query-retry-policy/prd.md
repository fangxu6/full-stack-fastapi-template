# Frontend Query Retry Policy

## Goal

Make frontend read requests resilient to transient failures without replaying
writes, authentication failures, validation failures, downloads, or cancelled
requests.

## Confirmed Current State

- The shared singleton `QueryClient` is owned by
  `frontend/src/app/query-client.ts` and is provided by `frontend/src/main.tsx`.
- TanStack Query v5's client default is three retries; the app now overrides it
  with `shouldRetryQuery` and `queryRetryDelay`.
- Generated OpenAPI `ApiError` does not retain response headers. The app-owned
  `OpenAPI.interceptors.response` hook converts HTTP 429 responses into a
  `RateLimitError` carrying the request method and `Retry-After` value without
  editing generated client files.
- Mutations retain TanStack Query's no-retry default. Scheduler queries with
  `retry: false` remain authoritative per-query overrides.
- Direct XLSX downloads use the generated request boundary and are outside
  QueryClient retry behavior.
- Implementation landed in `af11708` (`fix(frontend): scope automatic query
  retries`).

## Requirements

1. Apply the shared policy only to QueryClient queries: maximum two retries
   after the initial request, with 1,000 ms then 2,000 ms delays.
2. Retry only `GET`, `HEAD`, and `OPTIONS` requests when the failure is a
   response-less Axios network error or HTTP 408, 429, or 5xx.
3. Fail immediately for HTTP 4xx other than 408/429, unknown methods, write
   methods, cancelled requests, and aborted requests.
4. For HTTP 429, accept `Retry-After` delta-seconds or HTTP-date only when the
   computed delay is between 0 and 30 seconds inclusive; otherwise use the
   normal retry delay.
5. Preserve per-query `retry: false`, mutation no-retry behavior, existing
   401/403 session handling, and current loading/error surfaces.
6. Do not add dependencies, backend rate limiting, API schema changes, global
   retry UI, countdowns, or a global request timeout.

## Acceptance Criteria

- [x] Network errors and HTTP 408, 429, and 5xx retry at most twice.
- [x] HTTP 400, 401, 403, 404, and 422 do not retry.
- [x] POST, PUT, PATCH, DELETE, and unknown-method requests do not retry.
- [x] Cancelled and aborted requests do not retry.
- [x] Valid delta-seconds and HTTP-date `Retry-After` values control 429 delay.
- [x] Missing, invalid, past, or over-30-second values use 1,000/2,000 ms
      backoff.
- [x] Per-query `retry: false`, mutation behavior, and manual refetch retry
      budgets remain intact.
- [x] Focused retry tests pass; no generated client files or backend contracts
      changed.

## Out Of Scope

- Retrying mutations or direct file downloads.
- Client-side request timeouts, circuit breakers, global retry indicators, or
  user-visible countdowns.
- Backend rate limiting, `Retry-After` production policy, API schema changes,
  or generated-client regeneration.

## Decision

Use one app-owned retry predicate and delay function at the QueryClient
boundary. Keep 429 header capture in the existing OpenAPI response interceptor;
do not alter generated transport code. This is the smallest boundary that
protects all React Query consumers while preserving explicit per-query escape
hatches.
