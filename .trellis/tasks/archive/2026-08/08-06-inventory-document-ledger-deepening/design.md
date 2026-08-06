# Inventory document/ledger deepening design

## Module shape

Keep the existing bounded inventory module and add two focused implementations:

- `backend/app/modules/inventory/units.py`
  - owns processing/receiving unit list/create/update behavior;
  - owns normalized-name lookup and active-state validation;
  - exposes the minimum unit lookup seam used by document creation and imports.
- `backend/app/modules/inventory/documents.py`
  - owns document write operations;
  - owns document-line creation/replacement and ledger effects;
  - owns delete/restore ledger state changes and negative-balance validation;
  - owns applying an approved correction to an existing document;
  - may keep the existing document-public projection helper needed by write
    results, while list/detail query operations remain in `service.py`.

`backend/app/modules/inventory/service.py` remains the query-oriented inventory
module for document reads, balances, ledger reads, exports, suggestions, and
any unchanged query helpers. It no longer owns the moved write functions.

## Import compatibility boundary

- The standard document workbook import is the only recommended entry point for
  new inventory data.
- The legacy historical import remains a compatibility path for existing
  workbooks and historical reconciliation. It must continue to preserve raw
  source snapshots, legacy flags, and ledger traceability.
- This task must not delete historical import code, persisted historical data,
  or legacy tables. Historical import retirement is a separate decision and
  implementation task.

## Dependency direction

```text
router.py --------> units.py
router.py --------> documents.py ------> units.py
importer.py ------> units.py
importer.py ------> documents.py
correction_service.py -----------------> documents.py
daily_report.py --> service.py
service.py ------> documents.py   (only if it reuses the document projection)
```

The correction workflow remains the owner of request state, claiming, retry,
and audit orchestration. It calls the document/ledger module only for the
approved operation. The document/ledger module has no dependency on correction
workflow code.

## Transaction and error contracts

- Preserve caller-owned transactions. HTTP routes use the existing audited
  request session; CLI/background paths retain their explicit transaction
  phases.
- Preserve existing `flush`, nested savepoint, and rollback behavior.
- Preserve semantic `BadRequestError`, `ConflictError`, and `NotFoundError`
  behavior and let the global error handlers keep the `detail + request_id`
  envelope.
- Do not change schemas, SQLModel entities, migrations, permissions, or route
  paths.

## Test surface

- Add focused unit-module tests for unit normalization, active resolution,
  document/ledger effects, negative balances, delete/restore, and approved
  correction application.
- Keep API tests for permission, request transaction, response, and error
  behavior.
- Keep importer tests for workbook grouping, unit resolution, savepoints, and
  rollback; they should reach the new modules through their existing path.
- Keep legacy importer tests for reconciliation, raw source retention, and
  historical ledger export traceability.
- Keep correction API tests for request lifecycle behavior and the delegation
  result.

## Compatibility boundary

All current callers are repository-internal. Migrate them in the same change
and remove the moved write names from `service.py`; do not add a compatibility
facade that would leave two authoritative entrypoints.
