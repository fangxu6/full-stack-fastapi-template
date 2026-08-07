# Use BIGINT identity for new entity primary keys

## Status

Accepted. New independent internal entities use BIGINT identity keys; UUID is
still permitted only for a documented exception.

## Context

The database contains established UUID tables and newer operational tables.
Changing existing identifiers would break public and cross-module contracts,
while new internal rows benefit from compact sequential keys.

## Decision

New independent business entities use PostgreSQL `BIGINT GENERATED ALWAYS AS
IDENTITY` primary keys. Existing UUID tables remain unchanged, and a new
BIGINT-keyed table may retain UUID foreign keys to them. UUID remains a
documented exception for cross-system, offline, opaque-external, or
shared-UUID-primary-key cases.

`auth_session` is one such exception. Its UUID is an opaque, independently
created and revoked session identity exposed as the JWT `sid`; changing it to
BIGINT would alter the token contract and invalidate compatibility. Any future
migration would require an explicit compatibility-safe decision and token
transition plan.

## Consequences

- Technical primary keys are not business identifiers and may contain gaps.
- Future modules must declare their resource access domain; numeric IDs do not
  provide authorization.
- Public numeric IDs remain JSON numbers. Alerting starts at `2^53 - 1`, and
  the risk of JavaScript precision loss beyond that value is explicitly
  accepted rather than blocked by this decision.

## Related Decisions

- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0007: Require An Explicit Audit Actor](./0007-require-an-explicit-audit-actor.md)
