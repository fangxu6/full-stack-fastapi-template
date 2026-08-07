# ADR Audit

## Scope and Method

Reviewed all twelve original documents in `docs/adr/` against the current source
tree, tests, runtime configuration, and Trellis specifications. The follow-up
remediation also added ADR-0013, normalized the ADR index, and added an isolated
Alembic round-trip regression test. No production runtime or production
database was used.

The assessment distinguishes an invalid current assertion from a documentation
quality gap. A historical ADR can remain valuable when it is explicitly marked
deprecated or superseded; it should not be silently rewritten to hide a
subsequent decision.

## Findings

### P1 - ADR-0010's exception-detail prohibition needs a successor decision

**Category: factual drift and design risk.**

ADR-0010 says task signals never read, forward, or serialize exception data,
and that no task event contains exception text. The current implementation
deliberately does the opposite for `task_failure`: it passes the original
exception and traceback to `log_exception()` (`backend/app/core/celery.py:135`),
which emits `exc_info` through the stdout NDJSON sink
(`backend/app/core/observability.py:236`). The current logging specification
explicitly permits this restricted detailed-error path for Celery task failures
(`.trellis/spec/backend/logging-guidelines.md:13`, `:355-356`).

This is a real security and operational-policy change, not a wording fix.
Create a successor ADR that decides whether detailed task failures may reach the
stdout collector, its redaction, reader access, retention, and acceptable sink.
Keep ADR-0010 accepted for task-context validation and cleanup; supersede only
its exception-detail prohibition.

### P1 - ADR-0008 authorizes irreversible deletion without governance criteria

**Category: design risk.**

ADR-0008 says the removal migration destructively deletes AI history with no
archive or backup prerequisite (`docs/adr/0008-remove-ai-inventory-query-capability.md:9`).
The migration does drop the tables and enum types
(`backend/app/alembic/versions/6e8f2b1c4d7a_remove_ai_inventory_query_capability.py:36-42`).
The implementation therefore matches the ADR, but the decision lacks data
classification, retention ownership, an approval record, and an explicit
production precondition for destructive execution.

Revise ADR-0008 to require a documented data-retention/disposal decision and,
before production execution, either a verified recoverable backup or an
approved record that recovery is intentionally unavailable.

### P2 - ADR-0005 describes a retired Redis and Celery scope as current

**Category: factual drift.**

ADR-0005 limits Redis to the broker and short-lived task results and calls
`runtime.ping` the only initial task (`docs/adr/0005-use-celery-redis-for-background-runtime.md:3-5,13-14`).
The current configuration has a separate Redis cache URL
(`backend/app/core/config.py:73-88`), and the current task registry includes
outbox, scheduler, audit, and inventory work
(`backend/tests/core/test_celery.py:389-416`).

Retain the Celery/Redis decision, but move the original bootstrap scope into
historical Context. State the current three Redis roles and their database/key
separation, and link the outbox and scheduler ADRs.

### P2 - ADR-0001 is weaker than the adopted frontend boundary

**Category: factual drift and documentation improvement.**

ADR-0001 says a data-dense admin experience may use Ant Design
(`docs/adr/0001-use-ant-design-for-complex-admin-components.md:3`). The current
frontend component specification makes Ant Design the default for that class
of screen and defines the provider ownership and the `shared/excel` exception
(`.trellis/spec/frontend/component-guidelines.md:45,55,62,67`). The provider,
Ant Design 6 dependency, and a real Rules-page use already exist.

Revise ADR-0001 to record the now-default boundary and its exceptions. The
decision not to adopt `@ant-design/pro-components` remains valid.

### P2 - ADR-0004's UUID exception is not documented for auth sessions

**Category: documentation improvement.**

ADR-0004 requires a documented rationale for UUID exceptions to new
independent entities (`docs/adr/0004-use-bigint-identity-for-new-entity-primary-keys.md:3-8`).
`auth_session` is a later, independently created/revoked persistent record
with a UUID primary key (`backend/app/models/auth_session.py:14,22`), and that
UUID is exposed as the JWT `sid` (`backend/app/modules/auth/session.py:15`).
That can be an opaque-external-identity rationale, but it is not recorded.

Document the exception and why its external token contract requires it, or
decide a future compatibility-safe migration to BIGINT. Do not infer approval
from the implementation alone.

### P2 - ADR-0012 describes the pre-refactor topology as current

**Category: factual drift.**

ADR-0012 is Accepted and says the refactoring shape is implemented, but its
Context still says `SchedulerRun` lifecycle state is currently split across
`service.py` and `tasks.py` (`docs/adr/0012-concentrate-scheduler-run-lifecycle-state.md:20-32`).
The current source puts durable transitions in `run_lifecycle.py`
(`backend/app/modules/scheduler/run_lifecycle.py:50-227`), delegates from
`service.py` (`backend/app/modules/scheduler/service.py:299-323`), uses
`orchestration.py` for Beat/Worker coordination, and leaves `tasks.py` as a
thin Celery registration adapter (`backend/app/modules/scheduler/tasks.py:1-16`).

Revise Context into past tense and name the three current ownership boundaries.
Keep the decision itself; its transaction and locality rules are implemented.

### P2 - ADR-0008 lacks an isolated migration-chain regression

**Category: documentation improvement (verification gap).**

The AI-removal test checks the current schema excludes the retired objects, but
does not demonstrate `predecessor -> head -> predecessor -> head` migration
behavior. The current database guideline requires that isolated chain for a
destructive reversible migration. This is a verification gap, not evidence
that downgrade fails. Add that test when ADR-0008 is revised or when the
migration test suite is next touched.

### P2 - The ADR set has inconsistent lifecycle metadata

**Category: documentation improvement.**

Only ADR-0003, ADR-0011, and ADR-0012 expose an explicit status. ADR-0001,
ADR-0002, and ADR-0004 through ADR-0010 lack Status sections; most also omit
separate Context and Decision sections. This prevented stale initial scope in
ADR-0005 and ADR-0012 from being identifiable as historical without source
inspection.

Adopt one lightweight ADR template for all new decisions: Status, Context,
Decision, Consequences, and Related Decisions. Backfill the Status field first;
do not rewrite deprecated or superseded historical reasoning.

## Per-ADR Disposition

| ADR | Disposition | Category | Evidence / reason |
| --- | --- | --- | --- |
| 0001 | Revise | Factual drift / documentation improvement | Frontend boundary in [component guidelines](../../../spec/frontend/component-guidelines.md) (line 45) and Ant Design provider in `frontend/src/app/providers/AntdProvider.tsx`. |
| 0002 | Retain; add metadata | Documentation improvement | Lightweight item flow is the reference in [directory structure](../../../spec/backend/directory-structure.md) (line 59) and `backend/app/api/routes/items.py`. |
| 0003 | Retain as deprecated | Documentation improvement | Supersession is explicit in [ADR-0006](../../../../docs/adr/0006-use-request-scoped-unit-of-work-for-http-writes.md) (line 9) and the current write dependency `backend/app/api/dependencies/database.py:19-31`. |
| 0004 | Revise | Documentation improvement | UUID session contract is implemented in `backend/app/models/auth_session.py` and `backend/app/modules/auth/session.py`; rationale is now recorded in the ADR. |
| 0005 | Revise | Factual drift | Current Redis roles are defined in `backend/app/core/config.py:73-88`; task inventory is covered by `backend/tests/core/test_celery.py:389-416`. |
| 0006 | Retain; add cross-references | Documentation improvement | Request commit/rollback and post-commit cache invalidation are implemented in `backend/app/api/dependencies/database.py:19-31`. |
| 0007 | Retain; add metadata | Documentation improvement | Actor binding and audit-field enforcement are implemented in `backend/app/core/audit.py:91-139` and covered by `backend/tests/models/test_audit_actor.py`. |
| 0008 | Revise | Design risk / documentation improvement | Destructive SQL is in `backend/app/alembic/versions/6e8f2b1c4d7a_remove_ai_inventory_query_capability.py:36-42`; governance is now documented and the round-trip test is `backend/tests/models/test_ai_removal_migration.py:52-85`. |
| 0009 | Revise | Factual drift / documentation improvement | Per-job and per-kind throttling is implemented in `backend/app/modules/scheduler/scheduler_alerts.py:56-70`; the ADR now qualifies the scope and links the outbox contract. |
| 0010 | Retain; partially supersede | Factual drift / design risk | Failure details are read at `backend/app/core/celery.py:146-151` and emitted by `backend/app/core/observability.py:253-262`; ADR-0013 replaces only the exception-detail prohibition. |
| 0011 | Retain | Documentation improvement | The deferred boundary remains absent from `backend/app/api/main.py:13-26`; the archived task is linked from the normalized ADR. |
| 0012 | Revise | Factual drift | Current ownership is implemented in `backend/app/modules/scheduler/run_lifecycle.py`, `orchestration.py`, and `tasks.py`; the ADR now describes that topology. |

## Original Recommended Order

1. Resolve the ADR-0010 exception-detail policy with a successor ADR and
   explicit partial supersession.
2. Add data-disposal governance and a migration-chain regression to ADR-0008.
3. Correct factual drift in ADR-0005 and ADR-0012.
4. Normalize lifecycle metadata and cross-references, including ADR-0001,
   ADR-0004, ADR-0006, ADR-0007, and ADR-0009.

## Evidence Limits

Source, test source, migration source, configuration, and current repository
specifications were inspected. The focused migration test was run with
`uv run --env-file ../.env_test pytest tests/models/test_ai_removal_migration.py`
and passed (`2 passed`). The test creates and drops a temporary `_test`
database; no production runtime or production database was touched.

## Remediation Result

- ADR-0001 through ADR-0012 now have explicit lifecycle metadata and related
  decision links; stale current-state text was moved to historical Context.
- ADR-0010 remains accepted for task context and cleanup, while ADR-0013
  supersedes its exception-detail prohibition and records the restricted Celery
  failure exception and traceback boundary.
- ADR-0008 states the required data-disposal approval and backup/recovery
  preconditions; its migration now has an isolated `head -> predecessor ->
  head` regression test.
- `docs/adr/README.md` provides status and supersession navigation.
