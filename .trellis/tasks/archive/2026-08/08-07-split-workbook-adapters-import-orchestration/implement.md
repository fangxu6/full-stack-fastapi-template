# Implementation: Split Workbook Adapters From Import Orchestration

## Ordered Checklist

1. [x] Add `document_import_adapter.py` with a frozen document-group record and
   pure standard workbook read/group/consistency validation.
2. [x] Add `legacy_import_adapter.py` with frozen normalized movement/source
   records and the existing pure legacy parsing/normalization rules.
3. [x] Move standard parsing/group validation and legacy header/date/quantity/
   movement helpers out of `importer.py`; keep orchestration persistence and
   public import functions in place.
4. [x] Change legacy orchestration to consume normalized adapter records while
   preserving batch identity, source rows, units, ledgers, reports, savepoints,
   and caller-owned transaction behavior.
5. [x] Move pure parser tests to adapter-focused coverage and keep importer/API
   integration tests for persistence and rollback.
6. [x] Run focused core Excel, adapter, importer, and inventory API tests; then run
   backend lint/type checks and inspect changed-file scope.
7. [x] Record validation results, review no-transaction/no-ORM adapter invariants,
   commit, archive the Trellis task, and record the session.

## Validation Commands

From `backend/`:

```powershell
$env:POSTGRES_DB = "aiadmin_test"
uv run pytest tests/core/test_excel.py tests/modules/inventory/test_importer.py tests/modules/inventory/test_document_import_adapter.py tests/modules/inventory/test_legacy_import_adapter.py tests/api/routes/test_inventory.py
bash scripts/lint.sh
```

Also run `git diff --check` and confirm no schema, migration, generated-client,
or dependency changes.

## Review Gates

- Adapters import no `sqlmodel.Session`, inventory ORM table, audit helper, or
  transaction method.
- `importer.py` owns all persistence, batch identity, issue raising, and CLI
  transaction behavior.
- `documents.py` and `units.py` remain the domain write/lookup owners.
- Standard and legacy import outputs are unchanged for valid and invalid files.
- Full inventory test failures caused by existing shared test-database data
  are reported separately from failures in the changed path.

## Validation Record

- `POSTGRES_DB=aiadmin_test uv run pytest tests/core/test_excel.py tests/modules/inventory/test_importer.py tests/modules/inventory/test_document_import_adapter.py tests/modules/inventory/test_legacy_import_adapter.py tests/api/routes/test_inventory.py -q`
  passed: 57 passed, 2 skipped because the optional `hongxia` workbook fixtures
  are unavailable.
- `bash scripts/lint.sh` passed: mypy, ty, Ruff, and formatting checks passed.
- `git diff --check` passed.
- Adapter invariant review passed: no `Session`, ORM persistence, audit
  binding, commit, or rollback references in either adapter.
