# API E2E Validation Plan

## Environment

- Target backend: temporary local backend at `http://127.0.0.1:8000` (or a
  documented alternate free port).
- Health check: `/api/v1/utils/health-check/`.
- Isolation: PostgreSQL database `aiadmin_test`, migrated before startup through
  `POSTGRES_DB=aiadmin_test`. No shared development database is mutated.
- Setup: initialize twice, create an authenticated human administrator with the
  inventory and scheduler permissions, and retain a separate fresh database
  Session for persistence assertions.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | System Actor bootstrap and provisioning | Migrated `aiadmin_test` database | Start initialization twice; provision two custom keys twice | Initialization and provisioning succeed | Exactly one inactive, role-free System Actor exists for default key `system` and each custom key | Duplicate key cannot create a second actor; ordinary user has no system key |
| E2E-002 | Authenticated inventory audit create/update | Authenticated human with inventory permission | Create and update a processing unit or inventory document | Existing success shapes | Fresh Session sees creator/updater equal to the human on create; update changes only updater time/actor and preserves creator | Client audit fields remain schema-rejected; no second request transaction is needed for visibility |
| E2E-003 | Authenticated scheduler audit and manual origin | Authenticated human with scheduler permission | Create job, then request manual run/backfill | Existing job/run success shapes; run is `QUEUED` | Job audit fields are human-owned and `SchedulerRun.requested_by` equals the human UUID | No broker message is sent before the queued run commits; direct request payload has no audit fields |
| E2E-004 | System Actor public protection | Default and custom System Actors plus administrator | User list, direct user ID read, login, password recovery/reset, and role-replacement attempts | List omits each account; direct management read is non-disclosing; login/reset use existing generic failure semantics | System Actor fields and zero role assignments remain unchanged | No UUID, email, password, actor marker, or system key appears in public payload or log capture |
| E2E-005 | Internal no-actor and creator-tamper guard | Fresh Session with an audited model instance | Test-only internal write without binding; then modify persisted `created_by` | Internal operation raises before commit | Fresh Session finds no inserted/tampered business row | No NULL/sentinel actor row and no partial commit |

## Non-HTTP Coverage

- Scheduler unit/integration tests execute a manual run, retry/reclaim it, and
  assert its task-owned audited mutation and final `SchedulerJob` mutation use
  persisted `requested_by`; scheduled scan and scanner-only alert cases use
  System Actor.
- Inventory importer tests accept an active human or a pre-provisioned System
  Actor `actor_user_id`, reject a missing or inactive human actor, use a fresh
  Session to assert each generated audited row, and retain rollback on dry run
  or parse failure.
- Daily report/delivery tests assert their existing technical timestamps and
  state machines are unchanged; they do not acquire audit actor fields.

## Execution Notes

- All persistence checks use a new Session instead of the endpoint/worker ORM
  instance.
- No OpenAPI shape is intended to change. Regenerate the client only if an
  actual schema diff is introduced during implementation, then inspect the
  generated diff before staging it.
