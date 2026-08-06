# Inventory architecture deferred iterations

## Purpose

Keep the separate workbook-adapter candidate visible without expanding the
document/ledger deepening task.

## Deferred Items

| ID | Deferred scope | Reason | Dependency | Future deliverables |
|---|---|---|---|---|
| D-001 | Split modern and legacy workbook parsing into format adapters | It is a separate architecture candidate; this task only redirects existing calls to the new inventory seams | Current document/ledger module seams | Independent PRD, design, importer tests, and rollback review |
| D-002 | Retire the legacy historical import write path | Existing legacy documents, raw source rows, reconciliation, and ledger exports still depend on its compatibility contract | Inventory data inventory and operational confirmation that re-import is no longer needed | Deprecation/removal PRD, route and CLI retirement, traceability acceptance, follow-up migration review |

## Remaining Work In Current Scope

- D-001 is not required for this task's acceptance criteria.
- The current importer must continue to preserve its modern-template and legacy
  compatibility behavior.
- Standard document import is the recommended path for new data; D-002 must
  explicitly preserve reading and exporting existing historical data before any
  legacy write-path removal.
