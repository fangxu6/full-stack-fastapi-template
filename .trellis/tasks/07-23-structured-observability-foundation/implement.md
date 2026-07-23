# Structured Observability Foundation Implementation Plan

## Preconditions

- Keep this task in planning until the user reviews the final artifacts and
  explicitly approves `task.py start`.
- Preserve the parent backlog and this task's
  [deferred-iterations.md](deferred-iterations.md) boundaries.
- Do not add a collector, log store, dashboard, query endpoint, alert adapter,
  retry queue, or external-platform credential to application code.
- Use the documented 32-character lowercase hexadecimal request-ID contract;
  future Nginx deployment configuration is operational documentation, not a
  change to the current static frontend Nginx configuration.

## Implementation Order

1. Establish the typed observability core.
   - Add the bounded `structlog>=25,<27` dependency and
   `backend/app/core/observability.py`. Configure `structlog.contextvars`,
   the direct JSON renderer, and one stdout NDJSON sink.
   - Keep `log_event()` as the constrained facade for event name, severity,
     dependency name, allowlisted payload, stable SHA-256 sampling, and
     best-effort emission. It makes exactly one structlog call and never
     serializes arbitrary business values or exception objects.
   - Configure application and Uvicorn logging once in the FastAPI and startup
   entry paths through the structlog event facade. Disable Uvicorn's default
   access logger and suppress its server/error output. Remove direct
   `logging.basicConfig` and free-form application
     log calls that could carry exception values, paths, email recipients, or
     SMTP responses.
   - Add the two validated positive millisecond settings in
     `backend/app/core/config.py`; preserve the 90-second AI timeout.

2. Normalize request correlation and HTTP telemetry.
   - Replace the permissive request-ID middleware behavior in
     `backend/app/core/exceptions.py` with 32-character lowercase hexadecimal
     validation and `uuid4().hex` fallback.
   - Add a request-completion instrumentation boundary that measures a
     monotonic duration, derives the FastAPI route template after routing, uses
     `unmatched` instead of a raw URL when no template exists, selects the
     normal or AI threshold, and writes only the documented HTTP fields.
   - Preserve all existing response status, `detail + request_id` body, and
     `X-Request-ID` header behavior. Replace raw unhandled-exception logging
     with an allowlisted `http.request.failed` event.
   - Emit all `4xx/5xx` and slow requests, sample ordinary successful
     responses at the deterministic 10% rate, and ensure emission failure is
     not visible to the caller.

3. Add authentication, authorization, and dependency signals.
   - Update `get_current_user` in `backend/app/api/dependencies/auth.py`
     to mark only authenticated/anonymous request state; never write a user
     identifier, role, permission, or token into telemetry.
   - Emit `authorization.denied` from the semantic
     `PermissionDeniedError` path, keeping the existing `403` response and
     allowing the HTTP boundary to record its required `4xx` event.
   - Instrument `modules/ai/service.py` around the sidecar call with
     `ai_orchestrator` failure/slow events, without changing the current
     `ServiceUnavailableError` or timeout behavior.
   - Instrument `utils.send_email` for `smtp` failures only, omitting the
     recipient, message, and provider response. Pass request correlation only
     through safe request state when available.
   - Instrument database readiness and initial-data paths for credential-free
     `startup.failed` events named `postgres`, and the RBAC active-platform-
     administrator invariant for `iam_bootstrap`; preserve existing fail-closed
     startup behavior.

4. Scrub the optional Sentry integration.
   - Configure `backend/app/main.py` with hooks that remove request, user,
     breadcrumb, exception-value, stack-value, and arbitrary context/tag data
     before events or transactions leave the process.
   - Attach only normalized `request_id`, environment, and event name;
     preserve non-local opt-in initialization and make scrub failure drop the
     Sentry payload.

5. Document deployment and extend the backend specification.
   - Keep the Nginx request-ID overwrite/response-header snippet and stdout
     collector contract in task documentation for operations handoff.
   - Retain and refine the structured dependency registry in
     `.trellis/spec/backend/logging-guidelines.md` so new services must
     register a stable name before they emit failure or latency telemetry.
   - Do not modify the existing frontend-only Nginx configuration until a
     deployed API proxy is introduced.

6. Add tests and execute the quality gate.
   - Add focused core tests for schema rejection, JSON-line validity, event
     field allowlists, ID normalization, sampling stability, thresholds, and
     best-effort emission.
   - Adapt `backend/tests/api/test_platform_baseline.py` away from assertions
     that require raw `exc_info`; assert instead that forbidden values never
     appear and safe failure/HTTP events do.
   - Add AI, SMTP, startup, authorization, and Sentry-scrub tests according to
     [e2e-api-tests.md](e2e-api-tests.md).
   - Run focused backend tests first, then backend lint and the full backend
     test suite. No frontend generation is needed unless public API schemas
     change unexpectedly.

## Risk And Rollback Points

| Point | Risk | Required control | Rollback shape |
| --- | --- | --- | --- |
| Request-ID normalization | An unvalidated header becomes a log/sentry value or a proxy/direct route produces inconsistent IDs. | Regex validation, generated fallback, direct/proxy contract tests. | Revert telemetry code; existing public error body shape remains intact. |
| Root logger replacement | Third-party or legacy logs bypass JSON/redaction or logging failure affects requests. | Central allowlist emitter, no free-form app logging, best-effort write tests. | Restore prior handlers only as a short emergency measure; do not re-enable raw sensitive logging. |
| Structlog integration | A second logger API or processor chain permits arbitrary context to bypass the event contract. | Use one `log_event()` facade and direct JSON stdout sink; do not bridge arbitrary standard-library messages. | Disable the new dependency only with a tested standard-logging replacement; never fall back to free-form records. |
| Uvicorn logging | Default access/error output emits raw paths or tracebacks beside structured lines. | Disable default access output and suppress Uvicorn server/error loggers. | Keep the backend fallback but do not re-enable textual stdout logging. |
| Exception instrumentation | 5xx handler logs raw exception data or duplicates failures. | Replace `exc_info` path, assert one safe request failure event. | Revert handler change while retaining response contract. |
| Slow-route classification | AI traffic is logged as 1-second slow or telemetry changes its 90-second timeout. | Route-template classifier and separate sidecar timer tests. | Correct classifier/config; no data migration required. |
| Dependency instrumentation | SMTP/AI errors expose recipients, grants, questions, URLs, or provider data. | Typed stable-name helpers and redaction tests with sentinel secrets. | Remove helper call; original error mapping remains. |
| Sentry integration | SDK automatic context leaks data despite stdout redaction. | Explicit before-send and transaction scrub hooks with captured-payload tests. | Disable Sentry with `SENTRY_DSN` until configuration is corrected. |
| Nginx rollout | Duplicate response headers or mismatch between Nginx and backend ID. | Proxy integration validation before production rollout. | Backend fallback remains valid without Nginx. |

## Validation Commands

Run from the repository root unless stated otherwise:

```bash
cd backend && uv run pytest tests/api/test_platform_baseline.py tests/modules/ai/test_service.py
cd backend && uv run pytest
bash backend/scripts/lint.sh
```

Run the API scenarios in [e2e-api-tests.md](e2e-api-tests.md) against an
isolated test database. Validate deployment Nginx configuration with its
environment's configuration test command before enabling the public proxy.

## Review Gate Before Start

- [ ] PRD convergence pass contains no unresolved product or security decision.
- [ ] Design, implementation plan, and E2E plan agree on schema, sampling,
  thresholds, event names, dependency registry, Sentry redaction, and
  Nginx/direct-access correlation behavior.
- [ ] Deferred work is limited to the register; no alerting/audit/collector
  implementation appears in the current acceptance scope.
- [ ] The user has reviewed the planning artifacts and explicitly approved
  implementation.
