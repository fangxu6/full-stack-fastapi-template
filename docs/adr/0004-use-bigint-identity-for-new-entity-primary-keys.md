# Use BIGINT identity for new entity primary keys

New independent business entities use PostgreSQL `BIGINT GENERATED ALWAYS AS
IDENTITY` primary keys. Existing UUID tables remain unchanged, and a new
BIGINT-keyed table may retain UUID foreign keys to them. This preserves the
current contract while making new internal operational tables sequential and
compact; UUID remains a documented exception for cross-system, offline,
opaque-external, or shared-UUID-primary-key cases.

## Consequences

- Technical primary keys are not business identifiers and may contain gaps.
- Future modules must declare their resource access domain; numeric IDs do not
  provide authorization.
- Public numeric IDs remain JSON numbers. Alerting starts at `2^53 - 1`, and
  the risk of JavaScript precision loss beyond that value is explicitly
  accepted rather than blocked by this decision.
