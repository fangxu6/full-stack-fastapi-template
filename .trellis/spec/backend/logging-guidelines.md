# Logging Guidelines

> Logging expectations for backend operational and debugging paths.

---

## Overview

The backend emits a small, strict operational event stream. It preserves enough
safe context to correlate with the request ID returned to the client without
turning logs into a second store of user or business data.

---

## Current Reality

- `structlog>=25,<27` writes one newline-delimited JSON event per line to
  stdout through [`backend/app/core/observability.py`](../../../backend/app/core/observability.py).
- Request middleware binds a normalized request ID and emits the required HTTP
  outcome event without logging raw URLs, headers, query parameters, or errors.
- Dependency and startup paths call the constrained `log_event()` facade.

---

## Legacy Minimum Logging Rules

Earlier versions wrote free-form messages and exception details. Those legacy
behaviors are retired and are not permission to add free-form logs containing
request, resource, business, or credential identifiers.

---

## When to Log

- Unexpected exceptions
- External side-effect failures that need investigation
- Important startup or initialization checkpoints
- Important state transitions that are otherwise hard to reconstruct

---

## What Not to Log

- Passwords
- Raw auth tokens
- Secret configuration values
- Context-free noise such as `"error happened"` with no request or business correlation
- `print(...)` debugging in normal backend code paths

## Scenario: Structured Operational Dependency Events

### 1. Scope / Trigger

- Trigger: a backend path invokes, initializes, or otherwise depends on an
  external service whose failure or latency must be distinguishable in the
  externally managed operational-log platform.
- This is operational telemetry, not a durable page-access or business-action
  audit record. D-003 owns identity-traceable audit history.

### 2. Signatures

Structured events are newline-delimited JSON written to standard output through
`structlog` through its direct stdout JSON renderer. The first
dependency registry is:

| Dependency name | First owning path | Event trigger |
| --- | --- | --- |
| `postgres` | startup database connectivity or initialization | failure |
| `iam_bootstrap` | RBAC active-platform-administrator startup invariant | failure |
| `ai_orchestrator` | AI sidecar call | failure or elapsed time above the AI slow threshold |
| `smtp` | email delivery | failure |

New external services and named startup components use lowercase ASCII snake
case and must be registered in the owning module's implementation and tests
before emitting `dependency.failed`, `dependency.slow`, or `startup.failed`.

```python
log_event(
    dependency="ai_orchestrator",
    event_name="dependency.failed",
    request_id=request_id,
    elapsed_ms=elapsed_ms,
)
```

### 3. Contracts

- Every record has a schema version, event name, severity, environment, and
  timestamp. Request-scoped records also carry `request_id`.
- Dependency records carry an allowlisted `dependency` name and may carry
  `elapsed_ms` and `slow_threshold_ms`.
- The only HTTP metadata allowed is method, route template, status code, and
  elapsed time. Authentication metadata is limited to `actor_kind` and
  authorization outcome.
- Never emit bodies, query strings, headers, passwords, tokens, cookies, API
  keys, AI actor grants, raw AI questions, user UUIDs, raw exception messages,
  traceback values, or arbitrary resource/business identifiers.
- Application code only writes JSON to stdout. The runtime owns collection and
  external export; application code has no collector credential, buffer,
  persistence, or retry behavior.
- Uvicorn's default textual access log is disabled. Its server/error loggers
  must use the same safe structured handler or be suppressed; no default raw
  path, exception message, or traceback may share the stdout collector stream.
- Sentry is optional outside local environments. It uses the same redaction
  boundary and receives only `request_id`, environment, and event-name context.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Registered dependency fails | Emit one `dependency.failed` record with its stable name; re-raise or map the application error unchanged. |
| Registered dependency exceeds slow threshold | Emit `dependency.slow`; do not alter the existing timeout or response path. |
| Unknown dependency name | Reject during code review and tests; do not emit an ad hoc name. |
| Payload includes a forbidden field | Redact or omit it before serialization; logging must not fail the request. |
| Stdout sink fails | Preserve the business request path; best-effort logging must not become an availability dependency. |

### 5. Good / Base / Bad Cases

- Good: the AI sidecar times out after 12 seconds and emits
  `dependency.slow` with `dependency="ai_orchestrator"`, `request_id`, elapsed
  time, and the active 10-second threshold.
- Base: PostgreSQL is unavailable during startup and emits `startup.failed`
  with `dependency="postgres"`; no request ID exists yet.
- Bad: an SMTP exception serializes the recipient email or exception message
  into the log payload. That data is omitted and the record uses only
  `dependency="smtp"` plus safe operational fields.

### 6. Tests Required

- Unit test each initial dependency name and assert event name, severity,
  `request_id` behavior, duration fields, and JSON serialization.
- Redaction test forbidden payload values: token, cookie, email address, UUID,
  query string, request body, raw exception message, and AI question must not
  appear in the serialized output.
- Integration test a failed and slow AI dependency without changing its
  existing service-unavailable response or 90-second timeout contract.
- Startup test PostgreSQL/RBAC initialization failure remains fail-closed while
  producing a safe `startup.failed` record.

### 7. Wrong vs Correct

#### Wrong

```python
logger.error("mail failed recipient=%s error=%s", recipient, exc)
```

The record has an unstable source, exposes an email address and raw exception
content, and cannot be filtered reliably across services.

#### Correct

```python
log_event(
    dependency="smtp",
    event_name="dependency.failed",
    request_id=request_id,
)
```

The dependency source is stable and the payload stays inside the operational
allowlist. `log_event()` delegates to structlog; application modules must not
bind arbitrary request, actor, exception, or business context directly.

### 8. Precedence over Legacy Failure Logging

- For paths migrated to D-002 structured logging, emit exactly the allowlisted
  JSON record. Do not use `logger.exception`, `exc_info`, exception text, a raw
  URL path, or business/resource identifiers on the stdout collector path.
- Preserve the public API response contract, including `detail + request_id`.
  Observability must not change status-code mapping, response bodies, or the
  90-second AI timeout.
- The public Nginx location owns request-ID normalization: it overwrites the
  inbound `X-Request-ID` with `$request_id` before proxying and writes the
  response header. The backend is still the direct-access fallback: it accepts
  only a 32-character lowercase hexadecimal ID and replaces missing or invalid
  values with `uuid4().hex` before any structured record or Sentry context is
  created.
- Sentry configuration follows the same safe-context contract. It must not add
  raw request payloads or exception-message values outside the approved fields.

---

## Scenario: Structlog Application Logging

### 1. Scope / Trigger

- Trigger: backend code emits a D-002 operational event, binds request
  correlation, configures application logging, or adds a dependency/startup
  source.
- `structlog>=25,<27` is the application logging framework. It uses
  `structlog.contextvars`, an allowlisted facade, and its direct stdout JSON
  renderer; do not introduce Loguru or a JSON-only formatter package.
- This contract applies to application stdout. Collector deployment, log
  storage, dashboards, alert rules, and reader access remain operations-owned.

### 2. Signatures

```python
from typing import Literal

EventName = Literal[
    "http.request.completed",
    "http.request.failed",
    "authorization.denied",
    "dependency.failed",
    "dependency.slow",
    "startup.failed",
]

def configure_observability() -> None: ...

def bind_request_context(*, request_id: str, actor_kind: str = "anonymous") -> None: ...

def log_event(
    *,
    event_name: EventName,
    severity: str,
    request_id: str | None = None,
    dependency: str | None = None,
    elapsed_ms: int | None = None,
    slow_threshold_ms: int | None = None,
    method: str | None = None,
    route_template: str | None = None,
    status_code: int | None = None,
    actor_kind: str | None = None,
    authorization_result: str | None = None,
) -> None: ...
```

- `configure_observability()` runs once at each application/startup entry
  point. It configures `structlog.contextvars`, the direct JSON renderer, and
  one stdout NDJSON sink. Reconfiguration replaces the lazy logger so reload
  and test processes do not retain a stale output stream.
- Request middleware first clears context, then binds the normalized
  32-character lowercase hexadecimal `request_id`. It clears context at
  completion so a request cannot leak data into another request.
- `log_event()` is the sole application-owned entry point for D-002 records.
  It delegates one event to the configured structlog logger; it is not a
  second logging framework.

### 3. Contracts

- The structlog processor chain adds only timestamp, severity, environment,
  and bound safe context before `JSONRenderer`.
- Never configure `format_exc_info`, `dict_tracebacks`, an exception renderer,
  or arbitrary context processors on the stdout path.
- `request_id` and `actor_kind` are the only request context keys that may be
  bound with `structlog.contextvars`. Bind no user ID, email, role, permission,
  token, request body, header, query string, resource ID, or exception object.
- The facade accepts only the schema fields defined in the D-002 contract.
  Unknown or forbidden fields are omitted before the structlog call; a failed
  log serialization/write is swallowed so it cannot change a request, timeout,
  retry, or startup failure path.
- Do not bridge arbitrary standard-library records into the collector: their
  message values are not within this event schema. Disable Uvicorn's access
  logger in the production command and suppress its server/error loggers in
  application configuration rather than rendering raw messages or tracebacks.
- Application modules must not call `structlog.get_logger(...).bind(...)`,
  `logger.exception(...)`, or `logger.*(..., exc_info=...)` for operational
  records. Use `log_event()`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `configure_observability()` runs again in a reload/test process | Replace prior handlers; do not duplicate JSON lines. |
| Request ID is invalid or absent | Normalize/generate before binding; never bind caller text. |
| `log_event()` receives unknown/forbidden data | Omit it; do not serialize a fallback `repr` and do not fail the business path. |
| Event contains a dependency/source name not in the registry | Treat as code-contract failure in unit tests/review; do not ship an ad hoc source. |
| Structlog renderer or stdout write fails | Swallow the telemetry failure; preserve response/startup control flow. |
| Uvicorn emits default access/error output | Disable or suppress it; stdout must not contain a textual line. |
| A direct structlog bind appears in application code | Reject in review/tests because it bypasses the allowlist. |

### 5. Good / Base / Bad Cases

- Good: request middleware binds only
  `request_id="a3f..."`; `log_event(event_name="http.request.completed",
  severity="INFO", method="GET", route_template="/api/v1/users/{user_id}",
  status_code=200, elapsed_ms=12)` emits one JSON line.
- Base: a fast successful request falls outside the stable 10% sample bucket;
  `log_event()` emits nothing and the HTTP response remains unchanged.
- Bad: `structlog.get_logger().bind(email=user.email, token=token).error(...)`
  adds uncontrolled context that may be serialized. Do not use it.
- Bad: configuring an exception renderer makes traceback values appear in the
  collector stream. Do not configure it.

### 6. Tests Required

- Unit test processor configuration emits one parseable JSON record and is
  idempotent across repeated setup.
- Unit test context is cleared between sequential requests and only contains
  normalized request ID plus the allowed actor kind.
- Unit test the event facade omits sentinels for token, cookie, email, UUID,
  query, body, raw exception, and AI question; assert no `repr` or stack value
  appears.
- Unit test stable sampling and every mandatory unsampled event class.
- Integration test the production Uvicorn command and verify no default access
  line, raw URL, exception message, or traceback reaches stdout.
- Keep the dependency, AI timeout, startup fail-closed, and Sentry scrub tests
  specified in the D-002 E2E plan.

### 7. Wrong vs Correct

#### Wrong

```python
import structlog

log = structlog.get_logger()
log.exception("sidecar failed", url=url, actor_grant=actor_grant)
```

This lets arbitrary context and exception rendering cross the stdout boundary.

#### Correct

```python
from app.core.observability import log_event

log_event(
    event_name="dependency.failed",
    severity="ERROR",
    dependency="ai_orchestrator",
    request_id=request_id,
)
```

Structlog provides the JSON/context/stdlib machinery, while the facade keeps
the application's operational payload inside the reviewed contract.

---

## Current Reality vs Recommended Direction

### Current reality

- Logging is light and mostly centralized around failures and startup.
- `request_id` correlation is the strongest repo-wide operational guarantee.

### Recommended direction

- D-002 adopts `structlog>=25,<27` as the backend structured-logging framework.
- Keep `request_id` as the first-class correlation field and use the
  `log_event()` facade for all operational records.
- When adding logs around new modules or external integrations, register a
  stable source name and preserve the same allowlisted contract instead of
  inventing a different event format.

---

## Code Anchors

- Unhandled exception correlation: [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Operational helper logging: [`backend/app/utils.py`](../../../backend/app/utils.py)
- Startup logging: [`backend/app/backend_pre_start.py`](../../../backend/app/backend_pre_start.py), [`backend/app/initial_data.py`](../../../backend/app/initial_data.py)
