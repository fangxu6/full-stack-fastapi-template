# Excel Import and Export Contract

> Applies to `.xlsx` import and export behavior under `backend/app/**`.

## Boundaries

- Keep generic XLSX parsing, header mapping, limits, structured issues, and
  workbook rendering in `backend/app/core/excel.py`.
- Define workbook rows as Pydantic DTOs. Each exposed column uses
  `Field(alias=...)`; DTO declaration order is the template and export order.
  SQLModel entities must not gain spreadsheet aliases or file-only fields.
- Business grouping, master-data resolution, legacy layouts, and read-model
  joins remain in their owning module. Do not introduce a generic importer
  registry, DI container, or batch table for one module.

## Safety And Errors

- Accept only macro-free `.xlsx` uploads. Enforce the 10 MiB source size and
  10,000 nonblank data-row limits before domain persistence. `defusedxml` is a
  direct dependency so `openpyxl` parses untrusted XML defensively.
- Extra columns are ignored. Missing or duplicate declared headers, malformed
  workbooks, and row validation failures use `ExcelValidationError` with
  `worksheet`, `row`, `column`, `field`, and `message` for each issue.
- HTTP handlers must allow the existing `AppError` handler to produce the
  outer `{detail, request_id}` envelope. Do not replace an input failure with a
  bare FastAPI error or a partial error workbook.

## Inventory Ownership

- Standard inventory imports use the flat `InventoryDocumentExcelRow`, group by
  document number, require repeated header values to agree, and resolve only
  active existing processing/receiving units by normalized name.
- `POST /api/v1/inventory/excel/imports/documents` may receive repeated
  `document_types` query values. Page-specific callers must supply their
  allowed types; validate them after row DTO parsing and before grouping so an
  out-of-scope row retains its `单据类型` coordinate and rolls back the whole
  workbook. Omitting the parameter preserves the unrestricted CLI/API path.
- Each document group may use a savepoint to collect failures, but no import
  helper commits. `AuditedWriteSessionDep` owns the HTTP transaction; any issue
  raises after collection and rolls back the whole file.
- Historical import retains its path-based CLI wrapper. Its byte-source
  implementation, fingerprint, raw-cell snapshots, placeholder cleanup, and
  legacy unit auto-creation are compatibility behavior confined to
  `modules/inventory/importer.py`.
- Ledger XLSX exports query all matching non-deleted rows once, order by
  business date and entry identifier, and preserve legacy source details in
  remarks when no business document is linked.
- `GET /api/v1/inventory/excel/ledger` accepts optional
  `processing_unit_id`, `business_date_from`, `business_date_to`,
  `document_number`, and `receiving_unit_id`. Document-derived filters apply
  to the outer-joined document and therefore intentionally exclude historical
  adjustments without a linked document when they are present.

## Public Contract And Verification

- Inventory Excel import endpoints require `inventory.documents.manage`; ledger
  export requires `inventory.ledger.read`. Do not add a new permission or
  migration for this capability.
- Public route or response changes require `bash ./scripts/generate-client.sh`.
  Cover the core reader independently and test multipart imports, rollback,
  permissions, template output, legacy compatibility, and ledger filtering
  against `POSTGRES_DB=aiadmin_test`.
