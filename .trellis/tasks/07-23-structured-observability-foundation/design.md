# Structured Observability Foundation Design

## Scope And Boundaries

D-002 adds privacy-safe operational telemetry to the backend. It standardizes
request correlation, JSON event emission, redaction, sampling, dependency
signals, and Sentry scrubbing. It does not add a log database, collector,
dashboard, log-query API/UI, alert rules, notification adapters, durable
business audit, or any application-held external-platform credential.

The application writes one newline-delimited JSON object per event to stdout.
The runtime collects and exports those lines to an operations-owned platform.
Production retention is 30 days, staging retention is 14 days, and local
development has no persistence requirement. Only authorized operations
personnel receive reader access in that external platform. RBAC platform
administration does not imply log-reader access.

The deferred ownership boundaries are recorded in
[deferred-iterations.md](deferred-iterations.md). In particular, D-003 owns
durable, identity-traceable page-access and privileged-operation audit events.

## Architecture And Data Flow

```text
client -> Nginx (generate/overwrite request ID) -> FastAPI correlation guard
  -> authentication/permission dependency -> route/service -> response
  -> operational event builder -> stdout NDJSON -> runtime collector -> external platform
                                               -> optional scrubbed Sentry event
```

The existing `frontend/nginx.conf` serves static frontend assets and does not
currently proxy API traffic. The Nginx portion is therefore a deployment
contract for the later reverse-proxy configuration, not a claim about the
current development server.

### Request Correlation

`request_id` is a 32-character lowercase hexadecimal value.

1. The public Nginx location generates `$request_id`, overwrites the inbound
   `X-Request-ID` before proxying, and is the response-header authority. A
   deployment configuration uses the equivalent of:

   ```nginx
   proxy_set_header X-Request-ID $request_id;
   proxy_hide_header X-Request-ID;
   add_header X-Request-ID $request_id always;
   ```

2. The application accepts only `^[a-f0-9]{32}$`. It never copies an invalid
   caller-supplied header into an event, Sentry context, or response. Direct,
   missing, or invalid requests receive an application-generated `uuid4().hex`.
3. The response remains compatible with `X-Request-ID` plus `detail +
   request_id` error bodies. In a proxy deployment the Nginx-generated value
   is used end to end; in direct access the application-generated value is
   returned.
4. The same ID is forwarded to the AI sidecar. It is a correlation value, not
   an actor identity, authentication credential, or audit key.

### Structlog Event Pipeline

`structlog` is the application logging framework. It provides the long-lived
structured API, `contextvars` request correlation, and JSON rendering; it is
not a replacement for the D-002 data contract.

At startup, `app.core.observability` configures:

1. `structlog.contextvars` for the normalized `request_id` and optional safe
   `actor_kind`, clearing context at request entry and exit.
2. A processor chain that adds UTC timestamp, severity, environment, and the
   direct JSON renderer.
3. One direct stdout NDJSON sink for `log_event()` records. Arbitrary
   standard-library records are not bridged to the collector because their
   message values are outside the approved schema.
4. Uvicorn access logging is disabled in the production command and Uvicorn
   server/error loggers are suppressed; they never emit a separate textual
   stdout stream.

A small `log_event()` facade is the only application-owned entry point for
D-002 events. It takes a fixed event name plus typed allowed fields, rejects
unknown keys before binding them to structlog, applies stable sampling, and
never passes `exc_info` or an exception object. The facade is policy, not a
second logger: it delegates one structured call to the configured structlog
logger. Routes and services do not build arbitrary event dictionaries or use
format-string logging for operational telemetry.

Existing `logging.basicConfig`, `logger.error(..., exc_info=...)`, and
free-form SMTP/startup messages are removed or replaced. This prevents raw
exception text, recipient addresses, provider responses, tracebacks, and paths
from silently bypassing the event allowlist. Best-effort emission catches its
own serialization/write failure and never changes the business response,
retry, or timeout path.

### Schema

Each JSON line has these base fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | integer | yes | Starts at `1`; supplied by the `log_event()` facade. |
| `timestamp` | RFC 3339 UTC string | yes | Event creation time. |
| `severity` | `INFO`, `WARNING`, `ERROR`, or `CRITICAL` | yes | Determined by the event matrix. |
| `event_name` | approved event name | yes | One of the D-002 catalog values. |
| `environment` | `local`, `staging`, or `production` | yes | From validated settings. |
| `request_id` | 32 lowercase hex string | request-scoped only | Omitted for pre-request startup events. |
| `method` | HTTP method | HTTP events only | No request body, query, or raw URL. |
| `route_template` | route template or `unmatched` | HTTP events only | Derived from router metadata, never raw `path`. |
| `status_code` | integer | HTTP events only | Response status. |
| `elapsed_ms` | non-negative integer | timed events only | Measured with a monotonic clock. |
| `slow_threshold_ms` | positive integer | slow events only | Effective configured threshold. |
| `dependency` | registered stable name | dependency/startup events only | See registry below. |
| `actor_kind` | `anonymous` or `authenticated` | authorization context only | No user ID or user-derived identifier. |
| `authorization_result` | `denied` | `authorization.denied` only | No permission code in D-002. |

There are no arbitrary `extra`, message, exception, stack, actor ID, resource
ID, request URL, query string, header, body, user, or error fields. The event
builder rejects unknown fields before serialization. Values are emitted through
a JSON serializer, never interpolated into a format string.

### Event And Sampling Matrix

| Event | Trigger | Severity | Sampling |
| --- | --- | --- | --- |
| `http.request.completed` | Finished `2xx`, `3xx`, or `4xx` response | `INFO` for `2xx/3xx`, `WARNING` for `4xx` | Stable 10% only for ordinary non-slow `2xx/3xx`; always for `4xx` and slow requests. |
| `http.request.failed` | `5xx` response or an exception that escapes request processing | `ERROR` | Always. |
| `authorization.denied` | A semantic `PermissionDeniedError` after authentication state is known | `WARNING` | Always; it accompanies the corresponding `403` HTTP event. |
| `dependency.failed` | Registered dependency call fails | `ERROR` | Always. |
| `dependency.slow` | Registered dependency reaches its effective slow threshold | `WARNING` | Always. |
| `startup.failed` | PostgreSQL connectivity/initialization or RBAC startup invariant fails | `CRITICAL` | Always. |

For a normally successful request, `sha256(request_id)` is converted to a
deterministic bucket and emitted only when the bucket is within the fixed 10%
range. A retry carrying the same normalized request ID has the same decision.
The sample rate is deliberately fixed in this release; only slow thresholds
are environment-configurable.

All `4xx/5xx`, unhandled exceptions, authorization denials, slow requests,
and dependency failures are retained regardless of sampling. A `403` caused by
`PermissionDeniedError` produces both `authorization.denied` and the required
`http.request.completed` record. Authentication failures and framework `403`s
remain HTTP outcomes unless the semantic permission-denial exception is raised.

### Slow Thresholds

Add validated settings with these defaults:

| Setting | Default | Applies to |
| --- | --- | --- |
| `OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS` | `1000` | Every normal HTTP route. |
| `OBSERVABILITY_AI_SLOW_THRESHOLD_MS` | `10000` | `/api/v1/ai/inventory/query` and its `ai_orchestrator` call. |

The request logger selects the AI threshold for the AI query route template;
all other requests use the normal threshold. The sidecar call measures elapsed
time separately and emits `dependency.slow` at the same effective AI threshold.
The existing `AI_ORCHESTRATOR_TIMEOUT_SECONDS = 90` stays unchanged: slow
telemetry neither cancels work nor alters HTTP error mapping.

### Dependency Registry

| Stable name | Owning path | D-002 behavior |
| --- | --- | --- |
| `postgres` | database readiness and initial-data initialization | On failure emit `startup.failed` without `request_id`, then fail closed as today. |
| `iam_bootstrap` | `iam_service.ensure_bootstrap_state` active-platform-administrator invariant | On invariant failure emit `startup.failed` without `request_id`, then preserve the existing fail-closed startup behavior. |
| `ai_orchestrator` | `modules.ai.service.call_inventory_sidecar` | Measure the sidecar call; emit `dependency.slow` when applicable and `dependency.failed` for HTTP/value failures, then keep the existing `503` behavior. |
| `smtp` | `utils.send_email` | On send failure emit `dependency.failed` with the current request ID when one exists, then preserve existing caller error behavior. |

Future external dependencies and named startup components must register a
lowercase ASCII snake-case name in the owning module and tests before they can
emit a dependency or startup event. No DNS name, URL, vendor response,
recipient, model, or resource identifier is a permitted substitute for that
stable name.

### Authentication Context

The successful `get_current_user` dependency marks only
`request.state.actor_kind = "authenticated"`; absent or failed authentication
remains `anonymous`. Permission dependencies raise the existing
`PermissionDeniedError`; the semantic exception handler emits
`authorization.denied` with `authorization_result = "denied"`. Neither the
event nor the request state contains a user UUID, email, permission code, JWT,
or role.

## Sentry Contract

Sentry remains optional and is initialized only when `SENTRY_DSN` is set and
the environment is not `local`. Before sending either error or tracing data,
the SDK hook removes request data, headers, query strings, cookies, user data,
breadcrumbs, exception values, local variables, and arbitrary tags/context.
The remaining Sentry event receives only `request_id`, `environment`, and
`event_name` context. The hook may preserve Sentry's transport-level grouping,
but D-002 does not send raw exception messages or stack values. A scrub failure
drops the Sentry event rather than risking sensitive data.

Stdout remains the canonical D-002 operational signal. Sentry is independent:
failed Sentry delivery never buffers, retries, or changes application flow.

## External Operations Contract

The runtime attaches a line-oriented collector to stdout and exports to the
operations-selected Loki, ELK, or cloud-log system. It must:

- parse each line as JSON and reject/meter malformed records without creating a
  second application-side log store;
- retain production for 30 days and staging for 14 days; local has no required
  persistence;
- restrict read access to authorized operations personnel, separately from
  application RBAC;
- index only approved schema fields such as timestamp, event name, severity,
  environment, request ID, route template, status, and dependency;
- configure alert rules and routing outside the application.

Future alerting has a design-only, channel-neutral contract:

```text
Operational signal + approved rule -> notification intent
  -> one selected adapter (email | wecom | feishu | dingtalk | in_app)
  -> recipient and delivery policy
```

No Python interface, notification adapter, rule, recipient store, retry loop,
or in-app alert UI is created until a business owner supplies a real alert
condition and response policy.

## Compatibility, Rollout, And Rollback

- No database schema or generated frontend client changes are required.
- Add the bounded `structlog` dependency and configure its direct stdout JSON
  renderer; no Loguru, JSON-only formatter package, or second logging API is
  introduced.
- Existing response bodies and status-code mappings remain unchanged. The only
  header-format change is the request ID becoming a 32-character lowercase
  hexadecimal value.
- Rollout order: deploy the backend fallback first; then deploy Nginx with the
  overwrite/response-header contract; then enable the operations collector and
  retention/access configuration. The backend remains safe when any later
  layer is absent.
- Rollback: remove the Nginx request-ID override only after rolling back the
  backend; otherwise it continues safely accepting normalized IDs. Rolling back
  telemetry code restores prior logs but does not affect application data or
  API schemas. External platform retention and access policies remain
  operations-owned.

## Security Constraints

- Do not log request/response bodies, query parameters, headers, passwords,
  bearer tokens, API keys, cookies, SMTP credentials, actor grants, raw AI
  questions, user UUIDs, arbitrary resource identifiers, raw exception text,
  or traceback values.
- Do not make logging, Sentry, stdout, or the collector an availability
  dependency.
- Do not treat sampled logs as audit records, and do not add an application log
  reader endpoint or UI.
