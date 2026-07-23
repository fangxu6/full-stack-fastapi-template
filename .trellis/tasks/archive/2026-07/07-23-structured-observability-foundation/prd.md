# Structured Observability Foundation

## Goal

Provide privacy-safe, operationally useful backend telemetry: a stable request
correlation contract, newline-delimited JSON events, deterministic sampling,
safe dependency and startup signals, and an operations-platform handoff. D-002
must not become a durable business audit trail; that remains D-003.

## Confirmed Baseline

- The completed D-001 RBAC foundation defines users, roles, permissions, and
  the active Platform Administrator startup invariant.
- `RequestIdMiddleware` currently returns `X-Request-ID`; public error
  responses use `detail + request_id`. It currently accepts caller input
  verbatim and unhandled exceptions log a raw path and traceback.
- Sentry is optional through `SENTRY_DSN` outside `local`. The repository has
  no collector, log store, query UI/API, alerting service, or deployed API
  reverse proxy. The present `frontend/nginx.conf` serves static assets only.
- AI calls already forward a request ID to the sidecar and retain a fixed
  90-second timeout. SMTP email delivery, PostgreSQL readiness/initialization,
  and RBAC bootstrap are other operational failure boundaries.
- The parent backlog requires a structured schema, redaction, retention,
  sink/search/alert contract, instrumentation, and tests. It assigns durable
  page-access and privileged-operation evidence to D-003.

## Delivery Scope

D-002 delivers application-side structured JSON logging, redaction,
correlation, sampling, slow-request measurement, safe Sentry integration, and
an external-platform contract. The backend emits one JSON object per line to
stdout through `structlog`; runtime infrastructure collects and exports it.

Production records are retained externally for 30 days and staging records for
14 days. Local development has no persistent-retention requirement. Only
authorized operations personnel may read the external platform; application
RBAC platform administrators gain no implicit reader access. The application
has no log-query API or UI.

## Contracts

1. Each emitted event has schema version, UTC timestamp, severity, event name,
   environment, and the documented event-specific allowlist. Request-scoped
   records carry a normalized request ID.
2. The only request metadata permitted is HTTP method, route template, status,
   elapsed time, effective slow threshold, and normalized request ID.
   Authentication context is limited to `actor_kind` and
   `authorization_result=denied`; no user UUID, email, role, permission code,
   token, or credential is emitted.
3. Do not emit request/response bodies, query strings, raw URLs, headers,
   cookies, passwords, bearer tokens, API keys, SMTP credentials, AI actor
   grants, raw AI questions, arbitrary resource identifiers, raw exception
   messages, traceback values, or provider responses.
4. The only D-002 event names are `http.request.completed`,
   `http.request.failed`, `authorization.denied`, `dependency.failed`,
   `dependency.slow`, and `startup.failed`.
5. Every `4xx/5xx`, unhandled exception, permission denial, slow request, and
   dependency failure is emitted. Ordinary fast successful `2xx/3xx` requests
   use a fixed 10% stable decision derived from `sha256(request_id)`.
6. The normal HTTP slow threshold defaults to 1,000 ms. The AI query route and
   its sidecar call default to 10,000 ms. Both use validated environment
   settings, include the effective threshold in slow records, and never alter
   the existing 90-second AI timeout.
7. The operational-source registry is `postgres` for database
   readiness/initialization, `iam_bootstrap` for the RBAC active-platform-
   administrator invariant, `ai_orchestrator` for the AI sidecar, and `smtp`
   for email delivery. New external services or named startup components must
   register a lowercase ASCII snake-case name before emitting a dependency or
   startup event.
8. At the public edge, future Nginx generates `$request_id`, overwrites inbound
   `X-Request-ID`, forwards it to FastAPI, and owns the response header. The
   backend is the direct-access fallback: it accepts only a 32-character
   lowercase hexadecimal ID and generates `uuid4().hex` for missing or invalid
   values. Existing error response status/body semantics remain unchanged.
9. Stdout is application-owned NDJSON only. Default Uvicorn access logging is
   disabled in favor of `http.request.*`; Uvicorn server/error output must use
   the safe event handler or be suppressed. Logging, Sentry, stdout, and the
   collector never become availability dependencies.
   `structlog` is the application logging framework. Application events use a
   direct allowlisted JSON stdout sink; Uvicorn access logging is disabled and
   Uvicorn server/error records are suppressed rather than forwarded as raw
   standard-library messages.
10. Sentry remains optional outside `local`, is scrubbed before send, and
    receives only normalized request ID, environment, and event-name context.
    Request/user data, breadcrumbs, exception values, stack values, and
    arbitrary tags/context are removed; a scrub failure drops the Sentry event.
11. Runtime infrastructure, not this application, owns collector deployment,
    export to Loki/ELK/cloud logging, indexed search, dashboards, reader access,
    retention enforcement, alert rules, and on-call response.
12. Future important-business and timeout alerts use a design-only,
    channel-neutral notification contract that can select email, WeCom, Feishu,
    DingTalk, or in-app delivery. D-002 adds no alert rule, adapter, recipient
    persistence, retry loop, or Python interface.

## Acceptance Criteria

- [ ] Every captured stdout record is valid standalone JSON with only approved
  schema keys; sensitive sentinel values are absent from stdout and Sentry.
- [ ] Direct requests normalize invalid/missing IDs to 32 lowercase hex values;
  valid IDs remain stable, public responses retain their existing shape, and a
  future Nginx proxy has a documented overwrite/response-header test.
- [ ] Sampling is stable for a repeated request ID, while `4xx/5xx`,
  unhandled exceptions, authorization denials, slow requests, and dependency
  failures are always recorded.
- [ ] Normal and AI slow thresholds are configurable and recorded; an AI slow
  event does not cancel or reduce the existing 90-second timeout.
- [ ] `postgres`, `iam_bootstrap`, `ai_orchestrator`, and `smtp` failures emit
  only their stable source name and allowed fields while preserving existing
  error and fail-closed behavior.
- [ ] Default Uvicorn textual access/error output cannot bypass the structured
  stdout/redaction boundary.
- [ ] No database schema, frontend API, collector, log reader, dashboard,
  alert-delivery, or durable-audit feature is introduced.

## Out Of Scope

- Operating Loki, ELK, a cloud log service, or an alerting stack.
- Persisting, retrying, buffering, searching, or exposing operational logs in
  the application.
- Durable page-access/business-operation audit records, audit UI/API, or
  identity-traceable activity history.
- Alert rules, notification adapters, recipients, escalation, delivery retry,
  or in-app notifications.
- External API, scheduled-job, or MCP telemetry beyond shared D-002 contracts.

## Deferred Work

The promotion gates and future deliverables are recorded in
[deferred-iterations.md](deferred-iterations.md). Deferred work does not affect
this task's acceptance criteria.
