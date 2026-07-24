# ADR-0001: Internal Sentry Trace Correlation

## Status

Accepted

## Date

2026-07-24

## Context

The backend rebuilds Sentry error and transaction events through
`before_send` and `before_send_transaction`. Rebuilding rather than forwarding
the SDK event keeps requests, users, exception values, breadcrumbs, arbitrary
context/tags, and spans out of the Sentry transport.

The earlier D-002 design specified strict transaction context removal. The
current deployment is internal, however, and operators need a stable value to
correlate a Sentry transaction with distributed tracing during incident work.
The full Sentry trace context is not acceptable because it carries additional
fields that are neither needed nor approved at this export boundary.

## Decision

`scrub_sentry_transaction()` continues to construct a new minimal transaction
payload. It may add `contexts.trace.trace_id` only when the original value is a
canonical 32-character lowercase hexadecimal string (`^[a-f0-9]{32}$`). No
other source context is copied into the result.

Sentry SDK's `before_send_transaction` hook is the explicit reconstruction
boundary for this decision: it may return a newly built minimal transaction
payload rather than the SDK's original event. Rollback is deliberately simple:
remove the guarded `contexts.trace` reconstruction and strict mode is restored.

## Scope

- `backend/app/main.py` transaction scrubber
- `backend/tests/core/test_observability.py` Sentry scrub regression coverage
- `.trellis/spec/backend/logging-guidelines.md` export-boundary contract
- Internal Sentry transaction telemetry only

This does not change stdout Structlog events, HTTP/API payloads, request-ID
handling, Sentry error events, or Sentry's default PII setting.

## Alternatives Considered

### Preserve no trace context

- Option: Keep the prior strict contract and omit every Sentry trace field.
- Why not chosen: It prevents useful transaction-to-trace correlation for the
  internal operational workflow while retaining no additional user-facing
  privacy benefit over retaining one validated opaque identifier.

### Forward the SDK transaction context

- Option: Copy `event["contexts"]`, or retain more trace fields such as
  `span_id`, parent-span metadata, operation, and status.
- Why not chosen: The source event is not an allowlist and can expand with SDK
  behavior. Those fields are unnecessary for the approved correlation use case
  and would weaken the redaction boundary.

## Consequences

### Benefits

- Incident operators can correlate an internal Sentry transaction with a trace.
- The exported value has a narrow, deterministic format.
- The scrubber remains reconstructive and does not depend on the SDK event
  shape beyond one guarded field.

### Trade-offs

- A trace ID is intentionally exported to the internal Sentry deployment.
- Future consumers must not treat this exception as permission to retain other
  contexts or expand the transaction payload.

### Risks / Follow-ups

- If Sentry becomes externally accessible, privacy requirements tighten, or
  trace IDs become sensitive in this environment, return to strict mode using
  the rollback below.
- This ADR does not authorize retaining `span_id`, `parent_span_id`, request
  payloads, user identifiers, exception values, breadcrumbs, arbitrary tags,
  arbitrary contexts, or spans.

## Implementation Notes

- The scrubber uses a full-match regex for the canonical trace-ID form before
  adding the reconstructed `contexts.trace` object.
- The result remains a fresh event with fixed transaction metadata, safe tags,
  optional timestamps, and an empty span list.
- The logging guideline links this ADR so a future review sees both the narrow
  exception and the rollback path.

## Rollback

To restore strict Sentry mode:

1. Remove the guarded `safe_event["contexts"] = {"trace": {"trace_id": trace_id}}`
   assignment and its now-unused trace-ID matcher from
   `backend/app/main.py`.
2. Update the valid trace-ID test to assert that `contexts` is absent; retain
   the malformed/sentinel rejection test.
3. Remove the trace-ID exception from
   `.trellis/spec/backend/logging-guidelines.md` and mark this ADR superseded
   or deprecated with the date and reason.

The `before_send_transaction` hook and every other redaction rule stay in
place. No SDK configuration switch or event-schema migration is required.

## Validation

- A focused unit test proves a valid canonical trace ID is the only retained
  context field.
- A focused unit test proves malformed/sentinel trace IDs do not appear in the
  rebuilt event.
- The existing scrubber regression test proves request data, secrets, and spans
  remain absent.
- Backend lint/type checks and the observability test module must pass.

## Related Docs

- `docs/decisions/AI_CHANGELOG.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/log.md`
- `.trellis/tasks/archive/2026-07/07-23-structured-observability-foundation/design.md`
