# ADR-0002: Direct Structlog JSON Error Traces

## Status

Accepted

## Date

2026-08-01

## Context

The backend already uses structlog with one stdout NDJSON sink, but its safe-event
configuration renders `exc_info` as a boolean and discards exception detail. HTTP
500 and Celery failures therefore expose correlation without a root cause. The
system is internal and operators require original exception and traceback data.

## Decision

Keep structlog as the only application logging API and stdout as the only sink.
Insert `format_exc_info` before `JSONRenderer` and record unexpected HTTP and
Celery failures through a constrained exception entry point. Detailed error records
remain NDJSON and include the existing request/task correlation plus traceback.

Do not introduce standard-library logging handlers, stderr/file sinks, or Sentry
for this capability. Celery `task_failure` owns the failed event; `task_postrun`
only emits successful completion and clears context.

On Windows, PM2 must start the backend Python executable and Celery executables
directly. The previous `cmd /c` wrapper did not forward Python child output to
PM2. A Celery `setup_logging` receiver suppresses its default text handlers and
stdout redirection, while the global `-q` option suppresses its direct startup
banner, so structlog remains the only application output.

PM2 time prefixes are disabled for those three application processes because
structlog already provides the timestamp and the prefix would invalidate NDJSON.

## Scope

- `backend/app/core/observability.py`
- `backend/app/core/exceptions.py`
- `backend/app/core/celery.py`
- backend observability, API, and Celery tests
- `ecosystem.config.js`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/backend/error-handling.md`

## Alternatives Considered

### stderr plus standard logging

Rejected because it creates a second application API, sink, and routing model while
PM2 already captures the single process stdout stream.

### Sentry

Rejected because the user has decided to remove Sentry in a separate iteration.

### Keep safe events only

Rejected because request/task correlation alone cannot diagnose an internal failure.

### Keep `cmd /c` as the PM2 wrapper

Rejected because PM2 collected shell output but not Python/Celery child output on
Windows, leaving successful scheduler runs without observable lifecycle records.

## Consequences

### Benefits

- One JSON format and one PM2 collection path for normal events and failures.
- HTTP and Celery failures retain the root cause without changing business behavior.
- PM2 now collects direct Python/Celery stdout without a second logging sink.
- PM2 output lines remain directly parseable JSON.

### Trade-offs

- Internal operator logs contain original exception details and traceback values.
- `http.request.failed` and `task.failed` gain an optional `exception` JSON field.

### Risks / Follow-ups

- A PM2 executable change requires deleting and recreating that named process;
  `pm2 reload` does not replace an existing Windows executable.
- Future multi-sink or third-party logging needs may justify a separate standard
  logging integration task.
- Sentry removal remains D-001 in the active Trellis task.

## Validation

- HTTP and eager Celery failure tests assert one parseable detailed JSON event.
- Subprocess and PM2 probe tests prove stdout collection, including direct
  worker success and failure records.
- Backend static checks and quality hook pass.

## Related Docs

- `docs/decisions/AI_CHANGELOG.md`
- `docs/decisions/ADR-0001-internal-sentry-trace-correlation.md`
- `.trellis/tasks/08-01-scheduler-observability-diagnosis/prd.md`
