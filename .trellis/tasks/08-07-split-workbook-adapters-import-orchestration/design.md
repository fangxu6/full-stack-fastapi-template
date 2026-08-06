# Design: Split Workbook Adapters From Import Orchestration

## Module Shape

```text
inventory/router.py
  -> importer.import_document_workbook()
  -> importer.import_legacy_workbooks()

importer.py
  -> document_import_adapter.py   typed standard groups
  -> legacy_import_adapter.py     normalized legacy records
  -> units.py / documents.py      database-owned inventory writes
```

`importer.py` remains the stable orchestration interface. The two adapters are
format-specific readers/normalizers and are deliberately not database services.

## Adapter Contracts

### Modern document adapter

`read_document_workbook(content, allowed_document_types)` returns
`(groups, issues)`. A group is a frozen dataclass containing the document
number and the source `ExcelRow` values for that number. The adapter uses the
existing `read_xlsx_rows()` and `InventoryDocumentExcelRow` contract. It does
not resolve unit names or create documents; orchestration performs those
domain operations after it has the groups.

### Legacy workbook adapter

`read_legacy_workbooks(raw_content, raw_filename, finished_content,
finished_filename)` returns `(records, issues)`. A frozen legacy record carries
the normalized source metadata and a tuple of normalized movement records:

- workbook kind/name, worksheet, source row, raw cells, source balance
  snapshot, and cleanup flag;
- normalized item/unit/provenance fields;
- movement type, rolls/meters, business date, document number, and receiving
  unit name.

It uses `openpyxl` through the existing bounded loader and preserves the
historical header, placeholder, date, quantity, and movement rules. It does not
resolve units or write source/document/ledger rows.

## Orchestration Ownership

`import_document_workbook()` consumes document groups, aggregates adapter and
domain issues, resolves active units, builds `InventoryDocumentCreate`, and
uses the existing nested-savepoint plus document module write path.

`import_legacy_workbooks()` computes the fingerprint, creates the import batch,
consumes normalized legacy records, persists `LegacyImportRow`, resolves or
creates legacy units, writes documents/ledger rows, updates balances and the
reconciliation report, and raises the existing structured error. The caller
still controls the outer transaction.

`import_workbooks()` remains the compatibility CLI wrapper. Its current actor
binding, explicit commit/rollback, dry-run rollback, exception conversion, and
actor restoration remain unchanged.

## Error And Transaction Contract

- Adapter parse/normalization failures become `ExcelIssue` values with the
  same worksheet/row/field/message data as today.
- `ExcelValidationError` remains raised by orchestration, preserving the HTTP
  422 envelope and CLI conversion to `BadRequestError`.
- Adapters never receive `Session` and never call transaction or audit APIs.
- HTTP request transaction ownership remains in `AuditedWriteSessionDep`.
- CLI transaction ownership remains in `import_workbooks()`.
- Existing nested savepoints remain around standard document groups and legacy
  persistence rows where they currently protect partial work.

## Compatibility And Rollback

No models, schemas, migrations, route paths, permissions, dependencies, or
generated clients change. Existing internal parser test imports may move to
the adapter modules; public import entrypoints remain stable. Reverting the
source commit restores the current single-file implementation.

## Test Surface

- Pure adapter tests use in-memory XLSX bytes/workbooks and no database.
- Importer integration tests retain the existing database fixtures for unit
  resolution, persistence, rollback, fingerprinting, and reconciliation.
- Inventory API tests retain multipart HTTP coverage and legacy compatibility.
