# Inventory Excel Frontend Design

## Boundaries

- `shared/excel` owns file selection, client-side XLSX boundary checks,
  structured Excel-issue rendering, and authenticated binary downloads. It is
  generic and receives callbacks/URLs from a feature.
- Inventory owns the generated JSON/form API methods, page permissions,
  allowed document types, ledger kind, and page-filter mapping.
- The generated Axios client continues to own JSON and multipart calls. A
  small fetch-based binary helper uses the existing `OpenAPI` base URL, token,
  and credentials because the generated legacy Axios runtime cannot request a
  binary response safely.

## Data And Error Flow

```text
Inventory action -> shared dialog/helper -> inventory route -> service/importer
                 <- generated client/OpenAPI  <- typed endpoint contract
```

- `POST /excel/imports/documents` accepts repeated optional `document_types`
  query values. The importer checks typed row values before grouping/persistence
  and emits `ExcelValidationError` issues for disallowed rows.
- `GET /excel/ledger` accepts optional `document_number` and
  `receiving_unit_id`, in addition to its existing filters. A requested
  document-derived filter intentionally excludes legacy adjustments that have
  no linked document.
- A 422 response keeps `{ detail: { message, issues }, request_id }`. The
  shared dialog recognizes this exact shape and leaves all other errors to the
  standard `ApiError` path.

## UI

- The shared dialog uses Ant Design `Upload`, accepts one `.xlsx`, checks the
  10 MiB client limit, disables duplicate submits, and displays issue rows in
  an Ant Design table.
- `InventoryDocumentsPage` has text-and-icon commands in its existing toolbar:
  `下载模板`, `导入 Excel`, and `导出台账`. The first two require document manage;
  export requires ledger read.
- Raw passes `RAW_RECEIPT`/`RAW_RETURN` and `RAW`; shipment passes
  `FINISHED_SHIPMENT` and `FINISHED`. The existing filters supply the export
  query, then a successful import invalidates inventory queries and returns to
  page one.

## Explicit Non-Goals

- No type-specific template version, workbook annotation output, bulk-task
  persistence, route/menu change, or UI for the legacy two-workbook migration.
