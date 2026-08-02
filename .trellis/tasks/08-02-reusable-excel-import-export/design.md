# Reusable Excel Import/Export Design

## Boundaries

- `app.core.excel` owns safe XLSX byte parsing, DTO alias/header mapping,
  source locations, issue collection, template generation, and row rendering.
  It has no FastAPI, SQLModel, permission, or inventory business dependencies.
- Inventory DTOs and adapters remain module-owned. They translate typed Excel
  rows into `InventoryDocumentCreate`, resolve unit names, enforce group
  consistency, and delegate persistence to `inventory.service`.
- Routes own multipart reads, auth dependencies, response declarations, and
  downloads. Existing write-session dependencies own commit/rollback.

## Contracts

- Core parser input: workbook bytes, Pydantic row model, sheet name, and fixed
  limits. It reads in `openpyxl` read-only mode and returns typed rows paired
  with their worksheet coordinates or structured issues.
- Header mapping uses Pydantic aliases. Declared aliases must appear once;
  unknown columns are excluded before `model_validate`, so template users may
  retain notes or local columns.
- Core renderer uses the declared model field order and alias labels, then
  serializes DTOs with `by_alias=True` into a `BytesIO` workbook.
- `ExcelValidationError` is an `AppError` subclass with status 422. Its detail
  is `{ "message": ..., "issues": [...] }`, preserving the global outer
  `{ "detail": ..., "request_id": ... }` response envelope.

## Inventory Flows

### Standard documents

1. The template exposes one worksheet where every line repeats document type,
   date, document number, processing unit, receiving unit, and remarks.
2. The adapter validates typed line DTOs, groups by document number, rejects
   conflicting header values, resolves active unit names, and builds existing
   create schemas.
3. Each group is attempted in a nested transaction so expected service errors
   become group-bound issues. If any issue exists, the route raises once and
   the outer write-session dependency rolls back the entire workbook.
4. If no issue exists, the dependency commits all created documents together.

### Legacy migration

- Retain module-specific multi-row header discovery and historical parsing
  rules. Adapt its parsed mappings to the shared issue/source model rather than
  forcing those workbook shapes into the standard-row reader.
- Split the current path-and-commit function into a caller-owned import
  operation accepting named byte sources plus a path wrapper for the existing
  CLI. Keep source fingerprinting, persisted import batches, raw-cell
  snapshots, reconciliation reports, and legacy auto-created units unchanged.

### Ledger export

- Query ledger rows with outer joins to lines, documents, processing units, and
  legacy source rows. Apply the same predicates to the complete ordered result;
  never reuse a paginated route response.
- A ledger export DTO translates enum values to Chinese labels and emits dates,
  document number, unit names, item fields, roll/meter deltas, and remarks.
  Migration rows retain their source/reason and leave unavailable document
  fields empty.

## Compatibility And Security

- Add `defusedxml` as a direct backend dependency before accepting workbooks.
- Reject unsupported extensions, oversized bodies, invalid ZIP/XLSX content,
  missing sheets, and excessive data rows before business writes.
- No new table or Alembic migration is needed. Existing standard document
  audit fields and legacy import batches remain the audit record.
- Public endpoint changes require generated frontend client refresh even though
  this iteration adds no frontend workflow.
