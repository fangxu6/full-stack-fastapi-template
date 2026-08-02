# Configure frontend query retry policy

## Goal

Make frontend read requests retry only transient failures, without retrying
write operations or direct file downloads.

## Requirements

- Configure the shared TanStack Query client for at most two retries after the
  initial request.
- Retry network failures and HTTP 408, 429, and 5xx responses only.
- Fail immediately for every other HTTP 4xx response.
- Only retry `GET`, `HEAD`, and `OPTIONS` requests. Never retry an unknown or
  write-method request, even when it was started through `useQuery`.
- Never retry cancelled or aborted requests.
- Use a 1-second delay before the first retry and a 2-second delay before the
  second retry. For HTTP 429, a valid `Retry-After` response header overrides
  the corresponding delay.
- Accept both delta-seconds and HTTP-date `Retry-After` values only when the
  resulting delay is between 0 and 30 seconds. Absent, invalid, past, or
  over-limit values use the normal exponential backoff.
- Preserve the existing per-query `retry: false` overrides and mutation
  behavior.
- Do not add a dependency or alter generated OpenAPI client files.
- Do not add backend rate limiting or change the API contract. The frontend
  must honor a `429` and `Retry-After` header when a service introduces them.
- Do not add a global retry progress indicator or countdown. Existing loading
  and error surfaces remain unchanged.
- Do not add a global request timeout. This policy retries only failures
  reported by the browser or server.

## Acceptance Criteria

- [ ] A query retries a network error, HTTP 408, HTTP 429, and HTTP 5xx error
      at most two times.
- [ ] A query does not retry HTTP 400, 401, 403, 404, or 422 errors.
- [ ] A `POST`, `PUT`, `PATCH`, `DELETE`, or unknown-method request never
      retries.
- [ ] A cancelled or aborted request does not retry.
- [ ] A valid `Retry-After` header controls the delay for HTTP 429.
- [ ] Invalid or absent `Retry-After` values fall back to the normal retry
      delay.
- [ ] Both standard `Retry-After` formats are supported, and a delay longer
      than 30 seconds falls back to the normal retry delay.
- [ ] Existing scheduler queries with `retry: false` remain non-retrying.
- [ ] A user-triggered query refetch receives a new two-retry budget.
- [ ] Frontend type-check and focused tests pass.

## Notes

- The current QueryClient has no default options, so read queries use TanStack
  Query's broad default retry behavior. Mutations already default to no retry.
