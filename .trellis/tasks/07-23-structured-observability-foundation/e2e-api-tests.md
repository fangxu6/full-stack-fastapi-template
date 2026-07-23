# Structured Observability Foundation E2E API Tests

## Purpose

Validate the externally observable API contract and captured stdout/Sentry
payloads without introducing an application log-query endpoint. Every case uses
an isolated backend test database and captures the structured emitter or stdout
handler in-process.

## Test Fixture Rules

- Set a deterministic test environment and configure the two slow thresholds
  through settings overrides.
- Capture serialized stdout lines, parse each as JSON, and assert only the
  documented fields exist for the event under test.
- Exercise the public `log_event()` facade and the production Uvicorn command;
  stdout may contain only allowlisted JSON events and no default Uvicorn text.
- Use sentinel values for a bearer token, cookie, email, UUID, query string,
  request body, AI question, actor grant, SMTP password, exception message, and
  provider response. Each sentinel must be absent from every emitted line and
  Sentry payload.
- Do not assert arbitrary line ordering where a request can legitimately emit
  both an authorization/dependency event and an HTTP event. Identify records by
  `event_name` and normalized `request_id`.

## Request Correlation And HTTP Events

| ID | Setup and request | Expected API behavior | Expected telemetry |
| --- | --- | --- | --- |
| OBS-E2E-001 | Direct `GET /api/v1/utils/health-check/` with no request-ID header. | `200`; response has a 32-lowercase-hex `X-Request-ID`. | If sampled, one valid `http.request.completed` with route template, status, environment, and response ID only. |
| OBS-E2E-002 | Direct request with a valid 32-lowercase-hex ID. | Response echoes that ID. | Sampling decision equals the decision on a retry with the same ID. |
| OBS-E2E-003 | Direct request with an invalid ID containing the sentinel email/token. | `200`; response replaces it with a new valid ID. | Neither invalid input nor sentinel appears; any event uses the generated ID. |
| OBS-E2E-004 | Force a request ID whose stable hash is outside the 10% bucket on a normal fast `2xx` route. | Response remains `200`. | No `http.request.completed` event for that request. |
| OBS-E2E-005 | Force an in-bucket normal fast `2xx` route, then retry it with the same ID. | Both responses remain `200`. | Both requests make the same sample decision and emit valid identical-shape HTTP records if in bucket. |
| OBS-E2E-006 | Request an unknown route or missing authentication route. | Existing `404` or `401/403` response remains `detail + request_id`. | One unsampled `http.request.completed` with `WARNING`, safe route template or `unmatched`, status, and no raw path/query/header. |
| OBS-E2E-007 | Add a test route raising `RuntimeError` containing the exception sentinel. | Existing `500` response remains `detail + request_id`. | One unsampled `http.request.failed` with safe HTTP fields; no message, traceback, or sentinel. |
| OBS-E2E-008 | Add a normal test route delayed beyond the HTTP threshold. | Existing `2xx` response stays unchanged. | Unsampled `http.request.completed` contains elapsed time and the effective normal threshold. |
| OBS-E2E-009 | Delay the AI query route beyond the normal threshold but below the AI threshold. | Existing result/error contract remains. | It is not treated as a normal HTTP slow request; the effective threshold is the AI threshold. |

## Authorization, AI, And Dependency Events

| ID | Setup and request | Expected API behavior | Expected telemetry |
| --- | --- | --- | --- |
| OBS-E2E-010 | Authenticated zero-permission user calls an RBAC-protected route. | Existing `403` `detail + request_id`. | One `authorization.denied` with `actor_kind=authenticated` and `authorization_result=denied`, plus the required `4xx` HTTP record; no user ID, role, or permission code. |
| OBS-E2E-011 | Call a route with missing/invalid authentication. | Existing authentication error behavior remains. | Required HTTP `4xx` record only unless the semantic permission-denial exception is raised; it has no token/header values. |
| OBS-E2E-012 | Mock the AI sidecar to fail with sentinel URL/message/grant/question data. | Existing AI route maps the failure to `503`; persisted AI run behavior is unchanged. | One `dependency.failed` for `ai_orchestrator`, one required `5xx` HTTP record, no sentinels, and no changed 90-second timeout. |
| OBS-E2E-013 | Mock the AI sidecar to return after the AI threshold but before the 90-second timeout. | Existing successful result remains unchanged. | One `dependency.slow` for `ai_orchestrator` with elapsed and active AI threshold; request result is not canceled. |
| OBS-E2E-014 | Mock SMTP send to fail with recipient/provider/credential sentinels. | Existing caller exception behavior remains unchanged. | One `dependency.failed` with `dependency=smtp`; no recipient, email content, response, or credential appears. |
| OBS-E2E-015 | Mock PostgreSQL readiness/initialization to fail. | Startup exits/fails closed under the existing retry/initialization behavior. | One or more safe `startup.failed` records with `dependency=postgres`, `CRITICAL`, and no request ID, connection URL, credential, or exception text. |
| OBS-E2E-016 | Trigger the D-001 RBAC startup-invariant failure. | Initialization aborts without activating users or bypassing disabled status. | Safe `startup.failed` with `dependency=iam_bootstrap`, no credentials or account identity. |

## Sentry And Sink Safety

| ID | Setup and request | Expected API behavior | Expected telemetry |
| --- | --- | --- | --- |
| OBS-E2E-017 | Enable a test Sentry transport; trigger an unhandled exception containing all sensitive sentinels. | Existing `500` contract remains. | Captured Sentry event contains only normalized request ID, environment, and event name context; request, user, breadcrumb, exception-value, local-value, header, query, body, and sentinel data are absent. |
| OBS-E2E-018 | Enable a test Sentry transport; submit a slow AI request. | Existing request behavior remains. | Scrubbed transaction/error data contains no request body or URL/query data and does not change stdout behavior. |
| OBS-E2E-019 | Make stdout serialization/write raise. | API response, AI timeout, and exception mapping remain unchanged. | No fallback raw log is emitted; the failed operational event does not turn into a request failure. |
| OBS-E2E-020 | Verify a future Nginx deployment using the documented proxy configuration. | Nginx response contains exactly one valid request-ID header, matching the value received by the backend. | Backend events use that same normalized ID; a client-supplied invalid header never appears. |
| OBS-E2E-021 | Start the application with its Uvicorn logging configuration and make normal, failed, and startup requests. | Existing API behavior remains unchanged. | Captured stdout contains only parseable approved JSON events; no default Uvicorn access line, raw URL, exception text, or traceback appears. |
| OBS-E2E-022 | Send an unknown field and a forbidden exception value through the application event facade. | No request or startup behavior changes. | The facade rejects/omits the unknown values, and stdout remains valid allowlisted JSON; no processor renders a fallback `repr` or exception payload. |

## Completion Criteria

- Every captured stdout line is valid standalone JSON and contains an approved
  `schema_version`, `timestamp`, `severity`, `event_name`, and
  `environment`.
- Every event's keys are a valid subset for its event category; no arbitrary
  message/extra/error fields bypass the allowlist.
- All sentinel secrets and PII are absent from stdout and Sentry payloads.
- Existing public response status, body shape, request-ID behavior, AI timeout,
  and startup fail-closed semantics remain intact.
- The Nginx test is an operations/deployment gate once an API reverse proxy
  exists; its absence does not block local backend implementation.
