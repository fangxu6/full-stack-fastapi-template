# Reusable Excel import and export

## Goal

Provide a reusable `.xlsx` import/export capability for the FastAPI backend,
then use it for inventory document imports, legacy inventory migration uploads,
and human-readable raw/finished inventory ledger exports.

## Confirmed Facts

- `openpyxl`, Pydantic v2, FastAPI multipart handling, and inventory's
  router/service/schema boundary already exist.
- Standard inventory documents are nested header-plus-line records; the
  standard Excel template will be a single flattened worksheet grouped by
  document number.
- The existing legacy importer accepts two path-based workbooks, persists a
  fingerprinted import batch, preserves source rows, and remains callable from
  `backend/scripts/import_inventory.py`.
- Existing permissions are `inventory.documents.manage` and
  `inventory.ledger.read`; no new RBAC grant is required.

## Requirements

### R1: Reusable Excel contract

- Accept only `.xlsx` workbooks. Each uploaded workbook is limited to 10 MiB
  and 10,000 data rows.
- Map columns through Pydantic DTO `Field(alias=...)` values, retain DTO field
  order for templates and exports, and ignore undeclared worksheet columns.
- Report missing or duplicate declared headers, invalid workbooks, row limits,
  and Pydantic field errors with sheet, row, column, field, and message.
- Generate templates and exports as in-memory XLSX downloads. Do not add an
  Excel-specific dependency-injection container or persistence model.

### R2: Inventory imports

- Expose a standard inventory-document template and multipart import endpoint.
- Accept flattened document-line rows, resolve existing active units by name,
  group rows by document number, and reuse the existing document service for
  business validation and persistence.
- Validate every group and roll back the whole request when any parsing or
  business validation issue exists.
- Expose the existing raw/finished legacy workbook migration through multipart
  upload while preserving its source fingerprint, row snapshots, cleanup
  semantics, and path-based CLI entrypoint.

### R3: Inventory ledger exports

- Export raw or finished ledger details with required ledger kind and optional
  processing unit and business-date range.
- Include all matching rows without pagination in deterministic order and use
  human-readable Chinese business columns rather than internal UUIDs.

### R4: API and security contracts

- Add inventory REST endpoints for template download, standard import, legacy
  import, and ledger export.
- Import endpoints require `inventory.documents.manage`; ledger export requires
  `inventory.ledger.read`.
- Validation failures return HTTP 422 with the existing outer
  `detail + request_id` response contract and structured Excel issues inside
  `detail`.

## Acceptance Criteria

- [x] Core XLSX parsing and rendering are covered for aliases, ordering,
  ignored extra columns, invalid headers, invalid cells, empty rows, file/row
  limits, and broken workbooks.
- [x] Standard inventory imports create valid grouped documents and use active
  unit names; any validation or business issue leaves no document or ledger
  rows committed.
- [x] Legacy imports remain available to the CLI and HTTP callers, preserve
  their batch/audit behavior, and return the shared structured issue shape.
- [x] Raw and finished ledger downloads apply the selected filters, include
  human-readable provenance columns, and never silently paginate.
- [x] Endpoint permissions, 422 error shape, OpenAPI-generated client output,
  focused tests, and backend lint/type checks pass.

## Out Of Scope

- Frontend upload/download pages, CSV, `.xls`/`.xlsm`, async large-file jobs,
  error-annotated workbooks, configurable output columns, and generic template
  version compatibility.

Deferred work is tracked in `deferred-iterations.md`.
