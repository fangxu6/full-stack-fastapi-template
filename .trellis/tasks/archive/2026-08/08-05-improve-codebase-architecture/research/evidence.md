# Architecture review evidence

## Repository direction

- ADR-0002 keeps the repository as a modular monolith and reserves deeper
  module structure for genuinely bounded capabilities.
- ADR-0006 keeps the HTTP transaction boundary in `WriteSessionDep`; proposed
  deepening must not move commit/rollback ownership into a new module.
- The scheduler runtime source records PostgreSQL as source of truth and Celery
  as a numeric run-ID transport with lease-based dispatch.
- The frontend architecture source assigns global navigation and guards to
  `app/*`, business pages to `features/*`, and reusable permission predicates
  to `shared/*`.

## Hotspots

- `frontend/src/app/permissions.ts` is the centralized permission query seam,
  but `InventoryCorrectionsPage.tsx:92-105` bypasses it.
- `backend/app/modules/inventory/service.py` is 975 lines and spans units,
  document/ledger commands, balances, exports, and suggestions.
- `backend/app/modules/inventory/importer.py` is 805 lines and combines XLSX
  parsing, legacy compatibility, audit binding, persistence, and explicit
  transaction handling.
- `backend/app/modules/inventory/correction_service.py` is 960 lines and
  reaches into inventory service for ledger-effect checks and approved
  document mutations.
- `backend/app/modules/scheduler/service.py` is 536 lines and combines
  configuration, job management, run lifecycle, manual operations, cleanup,
  and bootstrap.
- `backend/app/modules/scheduler/tasks.py` is 370 lines and combines alerts,
  scan, dispatch, worker execution, and terminal state updates.

## Test locality

- Permission guard behavior is covered by
  `frontend/tests/permission-guards.spec.ts`, but the new correction page is
  not covered by the centralized permission-query contract test.
- Inventory mutation and import behavior is mostly exercised through
  `backend/tests/api/routes/test_inventory.py` and
  `backend/tests/modules/inventory/test_importer.py`.
- Scheduler definition and runtime behavior are split between
  `test_scheduler_service.py` and `test_scheduler_tasks.py`, matching the
  current split but leaving cross-file lifecycle behavior broad.

