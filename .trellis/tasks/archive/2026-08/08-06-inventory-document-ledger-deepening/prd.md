# Deepen inventory document ledger invariants

## Goal

Concentrate inventory document and ledger write invariants in explicit
inventory modules without changing the HTTP, database, Excel, or transaction
contracts.

## Requirements

- Add an inventory-unit module for the existing processing/receiving unit
  lifecycle: list, create, update, active-state validation, and normalized-name
  resolution.
- Add a document/ledger write module for document create/update/delete/restore,
  document-line and ledger effects, negative-balance validation, and execution
  of approved correction operations.
- Keep correction-request lifecycle orchestration in
  `correction_service.py`; it may call the document/ledger module, but the
  document/ledger module must not call back into correction workflow code.
- Keep document lists/details, balances, ledger reads, exports, and suggestions
  in the existing query-oriented module.
- Migrate every repository caller from the moved write functions and remove
  those write functions from `service.py`; do not retain compatibility shims
  for internal-only callers.
- Preserve current SQLModel entities, Pydantic schemas, semantic exceptions,
  savepoint behavior, request-scoped HTTP transactions, and explicit CLI/
  background transaction ownership.
- Keep the standard document import as the recommended new-data path while
  preserving legacy historical import compatibility, historical records, raw
  source traceability, and ledger export behavior.
- Add focused module tests while retaining API, correction, and importer
  regression coverage.

## Acceptance Criteria

- [ ] `units.py` owns unit lifecycle and active-name resolution; no production
      caller reaches moved unit functions through `service.py`.
- [ ] `documents.py` owns the document/ledger write invariants and approved
      correction execution; no production caller reaches moved write functions
      through `service.py`.
- [ ] `correction_service.py` remains the correction-request state machine and
      has a one-way dependency on `documents.py`.
- [ ] `service.py` retains query/read/export behavior only; no HTTP route,
      importer, correction path, or scheduled report loses behavior.
- [ ] Existing API responses, error messages/statuses, permissions, rollback
      behavior, and audit attribution remain unchanged.
- [ ] Focused unit/module tests cover units, document/ledger invariants, and
      correction application; existing inventory API/importer/correction tests
      pass in an isolated `_test` database.
- [ ] Backend lint, type checks, and relevant tests pass; no migration,
      generated-client, dependency, or unrelated formatting change is added.

## Constraints

- `WriteSessionDep`/`AuditedWriteSessionDep` remains the HTTP transaction owner;
  internal modules do not commit or roll back HTTP work.
- The Excel adapter split is a separate candidate and is deferred; this task
  only redirects the existing importer through the new inventory seams.
- Historical import retirement is a separate task; this task does not remove
  its route, CLI path, persisted data, or legacy tables.
- No new delete semantics, batch merge behavior, cross-domain unit relation,
  public endpoint, schema, entity, migration, or generic state-machine
  abstraction is in scope.

## Out Of Scope

- Splitting modern and legacy workbook parsing into separate adapters.
- Retiring the legacy historical import write path or deleting historical data.
- Rewriting balance/ledger query SQL or export projections.
- Changing inventory correction request states or retry policy.
- Adding a new API contract or changing generated frontend artifacts.
