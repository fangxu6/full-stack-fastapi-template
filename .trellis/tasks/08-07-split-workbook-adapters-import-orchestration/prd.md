# Split workbook adapters from import orchestration

## Goal

Separate the modern inventory workbook and legacy historical workbook format
rules from the inventory import orchestration. This should make each format
locally testable while preserving the existing document creation, legacy
traceability, transaction ownership, HTTP/CLI contracts, and database writes.

## Confirmed Facts

- `backend/app/modules/inventory/importer.py` currently contains standard
  document-template parsing, legacy header discovery, date/quantity
  normalization, movement inference, issue collection, batch identity,
  database writes, audit actor binding, and explicit CLI commit/rollback.
- The modern template and legacy raw/finished workbooks are two different
  format families with no shared row shape.
- The HTTP route calls `import_document_workbook()` and
  `import_legacy_workbooks()` with an `AuditedWriteSessionDep`; the path-based
  `import_workbooks()` wrapper is used by the CLI and explicitly owns its
  commit/rollback and audit actor restoration.
- `app.core.excel` already owns bounded XLSX reading, DTO alias mapping, and
  structured issue primitives. `documents.py` and `units.py` already own
  inventory document/ledger and active-unit operations.
- The prior Excel design explicitly preserves legacy compatibility and keeps
  adapters free of transaction ownership.

## Requirements

1. Add a modern document workbook adapter responsible for core XLSX reading,
   typed row grouping, allowed-document-type checks, and repeated document
   field consistency. It returns normalized document groups and structured
   issues without accessing the database.
2. Add a legacy workbook adapter responsible for workbook header discovery,
   raw/finished row extraction, date and quantity normalization, movement
   inference, and normalized legacy source/movement records. It returns
   structured issues without accessing the database.
3. Keep `importer.py` as the import orchestration module responsible for:
   - issue aggregation and raising the existing `ExcelValidationError`;
   - active unit resolution and existing document/ledger writes;
   - legacy import-batch fingerprint, source-row persistence, reconciliation
     report, and legacy movement persistence;
   - the public route-facing import functions;
   - the path-based CLI wrapper's explicit audit actor and transaction policy.
4. Keep adapters independent of `Session`, ORM entities, `commit()`,
   `rollback()`, audit actor binding, and route/task dependencies.
5. Preserve all existing import behavior: DTO aliases, limits, issue messages,
   row coordinates, group semantics, legacy raw-cell snapshots, cleanup flags,
   reconciliation openings, fingerprints, idempotency conflicts, document and
   ledger rows, and transaction boundaries.
6. Use existing dependencies and dataclasses/typed values only. Do not add a
   generic adapter registry, Excel DI container, new persistence, API route,
   schema, migration, or frontend client change.

## Out Of Scope

- Retiring or redesigning the legacy historical import path.
- Changing the standard or legacy API payloads, permissions, route paths, or
  generated client.
- Moving document/ledger business rules into adapters.
- Making adapters own commits, rollbacks, audit actors, or savepoints.
- Supporting new workbook formats, CSV, `.xls`, `.xlsm`, async import jobs, or
  configurable templates.

## Acceptance Criteria

- [ ] `document_import_adapter.py` and `legacy_import_adapter.py` contain no
      `Session`, ORM persistence, audit binding, commit, or rollback code.
- [ ] `importer.py` no longer contains format-specific header/date/quantity/
      movement parsing helpers; it retains orchestration and persistence only.
- [ ] Adapter tests run without the database and cover modern grouping,
      repeated-field mismatch, legacy header layouts, date parsing, quantity
      normalization, movement inference, and structured issues.
- [ ] Existing standard and legacy import integration tests pass, including
      all-or-nothing rollback, batch fingerprint conflict, source snapshots,
      reconciliation opening, and legacy HTTP compatibility.
- [ ] No API schema, route, migration, dependency, queue, or frontend client
      files change.
- [ ] Backend lint/type checks pass and the final diff contains only task,
      adapter/orchestration, and focused test files.

## Resolved Decisions

- Use two concrete adapter modules, one per real workbook family; two adapters
  make the format seam real and avoid a speculative generic registry.
- Keep adapter result dataclasses in their owning adapter modules rather than
  adding a third shared contract module.
- Keep the existing public functions in `importer.py` to avoid caller churn;
  only their internal parsing delegation changes.
- Let the orchestration layer aggregate adapter issues and retain all database
  and transaction behavior.

## Open Questions

None. The report solution and repository contracts define the required scope.

## Notes

This is a source-only architecture refactor. Existing import behavior is the
compatibility contract; no migration or generated-client synchronization is
expected.
