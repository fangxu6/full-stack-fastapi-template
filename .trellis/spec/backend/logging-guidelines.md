# Logging Guidelines

> Logging expectations for backend operational and debugging paths.

---

## Overview

The backend emits a small, strict operational event stream. Regular events
preserve enough safe context to correlate with the request ID returned to the
client without turning logs into a second store of user or business data.
Two restricted internal error events also preserve the original exception and
traceback for operations: unhandled HTTP 5xx and Celery task failure.

---

## Current Reality

- `structlog>=25,<27` writes one newline-delimited JSON event per line to
  stdout through [`backend/app/core/observability.py`](../../../backend/app/core/observability.py).
  The JSON object's first four fields are `timestamp`, `severity`, `source`,
  and `line`; no text prefix is added outside the JSON object.
- Request middleware binds a normalized request ID and emits the required HTTP
  outcome event without logging raw URLs, headers, or query parameters. Its
  unhandled-exception boundary emits one detailed `http.request.failed` event.
  It is a pure ASGI middleware registered outside CORS so CORS preflight
  requests also receive request correlation and safe HTTP telemetry.
- Dependency and startup paths call the constrained `log_event()` facade;
  HTTP and Celery failure boundaries call the restricted `log_exception()`
  facade.
- PM2 starts the backend Python executable and Celery worker/beat executables
  directly. On Windows, `cmd /c` captures shell-builtins but not the Python
  child output required by this collector contract.
- PM2 `time` is disabled for backend, worker, and beat. A PM2 timestamp prefix
  makes a JSON event line invalid NDJSON; event timestamps come from structlog.

---

## Contract Precedence

This living code-spec is the active runtime contract for backend operational
logging. Archived task PRDs and designs preserve the decisions made during
planning, but do not override this specification when an approach has since
been replaced.

`structlog.contextvars.merge_contextvars` intentionally adds safe execution
context to every event. HTTP requests bind `request_id` and the low-cardinality
`actor_kind` (`anonymous` or `authenticated`); Celery tasks bind only a
canonical, lowercase, hyphenated UUID `task_id` supplied by the caller and a
registered `task_name` belonging to the single application Celery instance.
Task identity reaches a lifecycle event only through `task_prerun`-validated
contextvars; neither logging facade accepts direct `task_id` or `task_name`
arguments. These fields must never expand into user, role, permission, token,
task argument, or business-resource identity.

---

## Legacy Minimum Logging Rules

Earlier versions wrote free-form messages and exception details. Those legacy
behaviors are retired and are not permission to add free-form logs containing
request, resource, business, or credential identifiers. Full exceptions are
permitted only through the two reviewed `log_exception()` call sites below.

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
| `smtp` | email delivery | failure |

New external services and named startup components use lowercase ASCII snake
case and must be registered in the owning module's implementation and tests
before emitting `dependency.failed`, `dependency.slow`, or `startup.failed`.

```python
log_event(
    dependency="smtp",
    event_name="dependency.failed",
    request_id=request_id,
)
```

### 3. Contracts

- Every record has a schema version, event name, severity, environment, and
  timestamp. Request-scoped records also carry `request_id`; task-scoped
  records carry only `task_id` and `task_name`.
- Dependency records carry an allowlisted `dependency` name and may carry
  `elapsed_ms` and `slow_threshold_ms`.
- The only HTTP metadata allowed is method, route template, status code, and
  elapsed time. Authentication metadata is limited to `actor_kind` and
  authorization outcome.
- Regular events must never emit bodies, query strings, headers, passwords,
  tokens, cookies, API keys, user UUIDs, raw exception messages, traceback
  values, or arbitrary resource/business identifiers. The restricted
  `log_exception()` path may render the original exception and traceback in
  its `exception` field for unhandled HTTP 5xx and Celery task failure only.
- Application code only writes JSON to stdout. The runtime owns collection and
  external export; application code has no collector credential, buffer,
  persistence, or retry behavior.
- `timestamp`, `severity`, `source`, and `line` are serialized before the
  remaining event fields so operators can see the time, level, callsite, and
  line at the start of each JSON line while collectors continue to parse the
  complete line as NDJSON. `source` is the fully qualified module/callable
  path of the actual caller, excluding the logging facade; `line` is its
  source line number.
- Uvicorn's default textual access log is disabled. Its server/error loggers
  must use the same safe structured handler or be suppressed; no default raw
  path, exception message, or traceback may share the stdout collector stream.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Registered dependency fails | Emit one `dependency.failed` record with its stable name; re-raise or map the application error unchanged. |
| Registered dependency exceeds slow threshold | Emit `dependency.slow`; do not alter the existing timeout or response path. |
| IAM bootstrap invariant fails during startup | Emit only `startup.failed` with `dependency="iam_bootstrap"`, roll back the session, and propagate a distinguishable already-recorded startup failure; the outer initialization entry point must not add `postgres`. |
| Database connection or session setup fails during startup | Emit only `startup.failed` with `dependency="postgres"`, then re-raise. |
| Unknown dependency name | Reject during code review and tests; do not emit an ad hoc name. |
| Caller supplies an arbitrary/forbidden facade field | Reject it at the closed Python call boundary before serialization; fix the caller and do not add `**kwargs` to accept it. |
| Stdout sink fails | Preserve the business request path; best-effort logging must not become an availability dependency. |

### 5. Good / Base / Bad Cases

- Good: an SMTP delivery attempt fails and emits `dependency.failed` with
  `dependency="smtp"`, without recipient or exception text.
- Base: PostgreSQL is unavailable during startup and emits `startup.failed`
  with `dependency="postgres"`; no request ID exists yet.
- Bad: an SMTP exception serializes the recipient email or exception message
  into the log payload. That data is omitted and the record uses only
  `dependency="smtp"` plus safe operational fields.

### 6. Tests Required

- Unit test each initial dependency name and assert event name, severity,
  `request_id` behavior, duration fields, and JSON serialization.
- Test the closed facade rejects an arbitrary keyword before serialization;
  supported dependency call paths must not derive their reviewed fields from a
  token, cookie, email address, UUID, query string, request body, or raw
  exception message.
- Integration test an SMTP failure emits only safe dependency fields and does
  not alter the outbox delivery state machine.
- Startup test PostgreSQL/RBAC initialization failure remains fail-closed while
  producing one safe `startup.failed` record for its actual root dependency;
  in particular, an IAM invariant failure emits only `iam_bootstrap` and never
  a second `postgres` event.

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

- For ordinary paths migrated to D-002 structured logging, emit exactly the
  allowlisted JSON record. Do not use `logger.exception`, `exc_info`, exception
  text, a raw URL path, or business/resource identifiers on the stdout
  collector path. The HTTP middleware and Celery `task_failure` receiver are
  the only reviewed `log_exception()` call sites.
- Preserve the public API response contract, including `detail + request_id`.
  Observability must not change status-code mapping or response bodies.
- The public Nginx location owns request-ID normalization: it overwrites the
  inbound `X-Request-ID` with `$request_id` before proxying and writes the
  response header. The backend is still the direct-access fallback: it accepts
  only a 32-character lowercase hexadecimal ID and replaces missing or invalid
  values with `uuid4().hex` before any structured record is created.

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
    "task.started",
    "task.completed",
    "task.failed",
]

def configure_observability() -> None: ...

def bind_request_context(*, request_id: str, actor_kind: str = "anonymous") -> None: ...

DetailedErrorEventName = Literal["http.request.failed", "task.failed"]

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

def log_exception(
    *,
    event_name: DetailedErrorEventName,
    exception: BaseException,
    traceback: TracebackType | None = None,
    elapsed_ms: int | None = None,
    method: str | None = None,
    route_template: str | None = None,
    status_code: int | None = None,
) -> None: ...
```

- `configure_observability()` runs once at each application/startup entry
  point, including the direct Celery worker import path
  `app.core.celery:celery_app`; FastAPI startup is not the worker's
  configuration path. It configures `structlog.contextvars`, the direct JSON
  renderer, and one stdout NDJSON sink. Reconfiguration replaces the lazy
  logger so reload and test processes do not retain a stale output stream.
- The Celery import path registers a `setup_logging` receiver before worker
  startup. Its presence prevents Celery from adding text handlers or redirecting
  stdout; it creates no application logger, handler, or additional sink.
- Request middleware first clears context, then binds the normalized
  32-character lowercase hexadecimal `request_id`. It clears context at
  completion so a request cannot leak data into another request.
- Register request correlation after `CORSMiddleware`, making it the outer ASGI
  layer under FastAPI's reverse middleware registration order. It must inject
  `X-Request-ID` in `http.response.start`, so a CORS-short-circuited `OPTIONS`
  preflight gets the same response correlation and allowlisted HTTP outcome
  telemetry without buffering or rebuilding its response.
- `log_event()` is the application-owned entry point for ordinary D-002
  records. `log_exception()` is its restricted companion for the two detailed
  error events. Both delegate to the same structlog logger and stdout sink;
  neither is a second logging framework.

### 3. Contracts

- The structlog processor chain adds timestamp, severity, environment, bound
  context, and `format_exc_info` before `JSONRenderer`. Only `log_exception()`
  passes `exc_info`, so ordinary events have no `exception` field.
- Do not configure `dict_tracebacks` or arbitrary context processors on the
  stdout path.
- `request_id` and `actor_kind` are the only HTTP context keys; `task_id` and
  `task_name` are the only Celery task context keys that may be bound with
  `structlog.contextvars`. Bind no user ID, email, role, permission, token,
  request body, header, query string, task argument, resource ID, or exception
  object. Task IDs are external correlation values, not broker-generated
  identity; invalid values are rejected rather than replaced with a new ID.
- The task name boundary requires the sender to belong to the application
  `celery_app`, the name to match the normalized dotted application-task
  syntax, and the name not to use a Celery framework prefix. Do not use the
  entire dynamic task registry as an allowlist or maintain a static list that
  can omit future application tasks.
- `log_event()` is a closed keyword-only interface containing only reviewed
  safe fields. Do not add `**kwargs`, mapping expansion, or a second generic
  event builder. Unknown fields are rejected at the Python call boundary and
  must be fixed during typing, tests, or review before deployment; they never
  reach the Structlog renderer. `task_id` and `task_name` are intentionally
  absent from this facade and can be attached only by validated task context.
  Best-effort handling applies only to serialization or stdout-write failures,
  which must not change a request, timeout, retry, or startup failure path.
- Do not bridge arbitrary standard-library records into the collector: their
  message values are not within this event schema. Disable Uvicorn's access
  logger in the production command and suppress its server/error loggers in
  application configuration rather than rendering raw messages or tracebacks.
- Application modules must not call `structlog.get_logger(...).bind(...)`,
  `logger.exception(...)`, or `logger.*(..., exc_info=...)` for operational
  records. Use `log_event()`, except the two approved boundaries that use
  `log_exception()`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `configure_observability()` runs again in a reload/test process | Replace prior handlers; do not duplicate JSON lines. |
| Request ID is invalid or absent | Normalize/generate before binding; never bind caller text. |
| A Celery task begins | The `task_prerun` signal clears prior context, validates the caller-provided canonical task ID and registered application task name, binds only those two fields, then emits `task.started` at `INFO`. |
| A Celery task succeeds | The `task_postrun` signal reads only allowlisted `state` plus the already-bound safe task context. It maps `SUCCESS` to `task.completed` at `INFO`; `RETRY`, `REJECTED`, `IGNORED`, `FAILURE`, unknown states, and rejected identities emit no postrun terminal event. It clears task context in `finally` for every exit path. |
| A Celery task fails | The `task_failure` signal emits one `task.failed` at `ERROR` through `log_exception()` when valid task context exists. It passes the original exception and traceback only; task arguments, keyword arguments, return values, and headers remain unread. |
| A Celery worker starts | The registered `setup_logging` receiver prevents Celery default handlers, formatters, and stdout redirection from taking over the NDJSON stream. |
| A Celery worker or beat starts under PM2 | Start the Celery command with global `-q` before `-A`; its direct banner print bypasses logging configuration and otherwise pollutes stdout. |
| PM2 changes a process executable | Delete and start the named application from `ecosystem.config.js`; do not rely on `pm2 reload` to replace an existing Windows process executable. |
| Celery passes signal payload extensions | The receiver may accept an opaque signal keyword mapping to satisfy Celery dispatch, but must delete it without reading, forwarding, or serializing args, kwargs, return values, or headers. |
| CORS preflight short-circuits the inner application | The outer request-correlation middleware adds `X-Request-ID` and emits the sampled/safe `OPTIONS` outcome event; it must not bypass correlation. |
| A caller supplies `task_id` or `task_name` to `log_event()` | Treat it as a programming error: the closed signature rejects it before serialization. Task identity can enter a lifecycle event only through validated `task_prerun` context. |
| A caller supplies an unknown/forbidden `log_event()` keyword | Treat it as a programming error: the closed signature rejects it before serialization. Fix the caller; do not add `**kwargs` to silently filter it. |
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
- Good: a task emits `task.started` and `task.completed` with only its validated
  `task_id` and registered `task_name`; a failed task emits one `task.failed`
  at `ERROR` with its original traceback in `exception`.
- Bad: `structlog.get_logger().bind(email=user.email, token=token).error(...)`
  adds uncontrolled context that may be serialized. Do not use it.
- Bad: another application module calls `logger.exception(...)` or adds
  `exc_info`; only `log_exception()` may render a traceback.

### 6. Tests Required

- Unit test processor configuration emits one parseable JSON record and is
  idempotent across repeated setup.
- Unit test context is cleared between sequential requests and only contains
  normalized request ID plus the allowed actor kind.
- Unit test the closed event facade rejects an arbitrary keyword before it can
  reach the renderer. Supported call sites must pass only reviewed fields and
  must not derive them from tokens, cookies, email addresses, UUIDs, queries,
  bodies or raw exceptions.
- Unit test direct `task_id` and `task_name` facade arguments are rejected
  before serialization. Use a real eager failure followed by a success task to
  prove lifecycle identities remain context-only, the failure has one ERROR
  event with traceback, and task context is cleared between executions.
- Unit test stable sampling and every mandatory unsampled event class.
- Integration test an allowed CORS preflight returns `X-Request-ID` and, with
  deterministic sampling, emits an allowlisted `http.request.completed` event
  for `OPTIONS` without a raw origin or URL.
- Integration test the production Uvicorn command and verify no default access
  line or raw URL reaches stdout; an unhandled exception must instead produce
  one parseable `http.request.failed` JSON record with `exception`.
- Runtime-test a PM2-managed `runtime.ping` task after process recreation and
  assert `task.started` and `task.completed` are raw JSON lines in its out log,
  without new stderr output or Celery text prefixes.
- Keep the dependency, task-lifecycle, and startup fail-closed tests specified
  in the D-002 E2E plan.

### 7. Wrong vs Correct

#### Wrong

```python
import structlog

log = structlog.get_logger()
log.exception("mail failed", recipient=recipient)
```

This lets arbitrary context and exception rendering cross the stdout boundary.

#### Correct

```python
from app.core.observability import log_event

log_event(
    event_name="dependency.failed",
    severity="ERROR",
    dependency="smtp",
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
- Keep `request_id` as the first-class correlation field and use `log_event()`
  for ordinary operational records or the restricted `log_exception()` error
  boundary.
- When adding logs around new modules or external integrations, register a
  stable source name and preserve the same allowlisted contract instead of
  inventing a different event format.

---

## Code Anchors

- Unhandled exception correlation: [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Operational helper logging: [`backend/app/utils.py`](../../../backend/app/utils.py)
- Startup logging: [`backend/app/backend_pre_start.py`](../../../backend/app/backend_pre_start.py), [`backend/app/initial_data.py`](../../../backend/app/initial_data.py)
