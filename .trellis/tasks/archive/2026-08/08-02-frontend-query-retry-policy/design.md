# Design: Frontend Query Retry Policy

## Boundary And Data Flow

```text
OpenAPI response interceptor -> RateLimitError (429 headers)
  -> QueryClient defaultOptions.queries
  -> shouldRetryQuery(failureCount, error)
  -> queryRetryDelay(retryAttempt, error)
  -> TanStack Query retryer
```

`ApiError` supplies method/status for generated requests. Axios supplies
response-less network failures and response headers. The retry policy is
frontend application code under `app/*`; generated client files remain
unchanged.

## Retry Contract

| Failure | Read method | Write/unknown method |
| --- | --- | --- |
| Network error with no response | retry twice | no retry |
| 408 or 429 | retry twice | no retry |
| 5xx | retry twice | no retry |
| Other 4xx | no retry | no retry |
| Abort/cancel | no retry | no retry |

The retryer receives `failureCount` starting at zero. The predicate allows
counts 0 and 1, so two retries occur after the initial request. Delay indexes
are 1,000 ms and 2,000 ms; a bounded 429 header replaces the matching delay.

## Compatibility

- TanStack Query v5 function options accept `(failureCount, error)` for both
  `retry` and `retryDelay`.
- A per-query `retry: false` option overrides the client default.
- Mutations use their existing default and are not assigned this policy.
- Manual `refetch()` starts a new fetch/retry sequence; it does not reuse a
  previous failure budget.
- Existing QueryCache/MutationCache session invalidation remains unchanged.

## Risks And Rollback

The main risk is misclassifying a request method or losing 429 headers before
the generated client turns the response into `ApiError`. Tests cover both
boundaries. Rollback is a one-file QueryClient/interceptor removal plus the
focused test removal; no schema or data migration is required.
