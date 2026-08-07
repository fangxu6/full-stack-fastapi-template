# ADR Remediation Design

## Boundaries

The remediation updates architecture records and one regression test. It does
not change application behavior, public API schemas, generated clients, Redis
configuration, or logging implementation.

## Decision Recording

- Backfill a common ADR shape: Status, Context, Decision, Consequences, and
  Related Decisions where applicable.
- Preserve historical decisions. ADR-0003 remains deprecated. ADR-0010 keeps
  its accepted task-context and cleanup rules; only its task-exception
  prohibition is superseded by ADR-0013.
- Add ADR-0013 to record the currently implemented restriction that only the
  unhandled Celery task-failure boundary may send its original exception and
  traceback to the structured logging sink. Arguments, headers, recipients,
  user/resource identifiers, credentials, and arbitrary context remain
  prohibited. Operations owns collector access and retention.
- ADR-0008 records governance required for future destructive retirement work;
  it does not claim that deleted historical AI rows can be recovered.

## Migration Regression

The AI removal test creates a temporary PostgreSQL database whose name ends in
`_test`, runs the complete Alembic chain to `head`, downgrades to the removal
migration's predecessor, inspects that the retired objects exist, upgrades to
`head`, inspects their absence, and repeats the downgrade/upgrade cycle. A
`finally` block disposes the temporary engine and drops the temporary database,
leaving the shared test database untouched. It checks schema shape only and
inserts no historical AI data.

## Risks

- The temporary database must be creatable by the configured PostgreSQL test
  user. The generated name is constrained to the approved `_test` suffix and
  cleanup runs in `finally`.
- ADR-0013 documents the established logging contract but cannot configure the
  external collector. The ADR assigns reader access and retention to
  operations rather than inventing undeployed controls.
