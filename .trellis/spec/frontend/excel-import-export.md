# Excel Import and Export

> Applies to browser XLSX workflows under `frontend/src/**`.

## Scenario: Browser XLSX Workflow

### 1. Scope / Trigger

- Trigger: a feature adds an XLSX template download, XLSX upload, or structured
  Excel validation feedback.
- Shared UI belongs in `shared/excel` only when it stays free of feature
  permissions, endpoint paths, and business labels. Features own those values.

### 2. Signatures

- `downloadXlsx({ url, filename, query })` performs an authenticated GET and
  writes a browser download.
- `ExcelImportDialog` accepts `onDownloadTemplate`, `onImport`, `onClose`, a
  title, and open state; it accepts exactly one workbook.
- Inventory standard import uses generated
  `InventoryService.importDocumentsFromExcel({ documentTypes, formData })`.
- Inventory ledger export uses `/api/v1/inventory/excel/ledger` with
  `ledger_kind`, optional date/unit/document-number filters, and optional
  `receiving_unit_id` for shipments.

### 3. Contracts

- The browser accepts only `.xlsx` and rejects files larger than 10 MiB before
  upload. The backend remains authoritative for MIME, workbook, row, and
  business validation.
- JSON and multipart requests use `frontend/src/client/**`. The current legacy
  Axios generator emits FastAPI binary form fields as `string`; a narrowly
  documented `File as unknown as string` cast is permitted only at that
  generated-client boundary because its runtime correctly appends `Blob`s.
- XLSX responses do not use the generated Axios client: its runtime does not
  request binary data. `downloadXlsx` must derive base URL, token, and
  credentials from `OpenAPI`, parse `Content-Disposition`, and throw the
  normal `ApiError` shape for non-success responses.
- Excel 422 errors are `{ detail: { message, issues }, request_id }`. Render
  worksheet, row, column, field, and message; preserve `request_id` for
  investigation even when it is not displayed in the table.

### 4. Validation And Error Matrix

| Condition | Required behavior |
| --- | --- |
| Non-XLSX or over-limit file | Block in dialog; do not submit a request |
| Server Excel 422 | Keep dialog open and render all issue coordinates |
| Other API error | Preserve `ApiError` handling and show generic failure feedback |
| Missing document-manage grant | Do not mount template/import controls |
| Missing ledger-read grant | Do not mount export control |
| Scoped page imports another type | Backend returns positional 422 and rolls back all rows |

### 5. Good / Base / Bad Cases

- Good: raw and shipment pages reuse `ExcelImportDialog` while passing their
  own allowed types, permissions, ledger kind, and filters.
- Base: a feature without an XLSX endpoint adds no shared dependency.
- Bad: put inventory-specific service calls in `shared/excel`, or hand-edit
  generated client files to force binary responses.

### 6. Tests Required

- Unit-test extension/size validation, `ApiError` 422 issue extraction, and
  content-disposition filename fallback.
- Browser-test command visibility, binary downloads, filtered export requests,
  a valid file-selection path, and rendered 422 issue cells.
- API-test import type scopes, full rollback, and each document-derived ledger
  export filter. Regenerate the client after endpoint contract changes.

### 7. Wrong vs Correct

#### Wrong

```ts
await InventoryService.exportInventoryLedger({ ledgerKind: "RAW" })
```

The generated legacy Axios client treats the XLSX response as ordinary data and
can corrupt the download.

#### Correct

```ts
await downloadXlsx({
  filename: "inventory-ledger-raw.xlsx",
  query: { ledger_kind: "RAW" },
  url: "/api/v1/inventory/excel/ledger",
})
```

This is the single binary-response escape hatch; all JSON/multipart calls stay
on generated services.
