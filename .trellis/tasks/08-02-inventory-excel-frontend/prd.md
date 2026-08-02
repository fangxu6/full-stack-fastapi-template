# Inventory Excel frontend workflows

## Goal

Deliver the first reusable browser workflow for the existing XLSX import and
export APIs, beginning with raw-inventory and finished-shipment document pages.

## Requirements

- Provide a domain-neutral single-XLSX import dialog and binary XLSX download
  helper under `frontend/src/shared/excel/`; they must not encode inventory
  permissions, document types, or endpoint paths.
- Add template download, standard document import, and ledger export commands
  to `/inventory/raw` and `/inventory/shipments` through their shared document
  page. Commands remain permission-gated: document manage for template/import,
  ledger read for export.
- Standard imports from each page must be enforced server-side to that page's
  document types. Any out-of-scope row reports a structured 422 issue and
  rolls back the complete workbook.
- Ledger XLSX export must respect the document-page date, processing-unit,
  document-number, and receiving-unit filters. Preserve the existing export
  rule that only active ledger rows are exported.
- Reuse the generated OpenAPI client for typed JSON/form requests. Do not
  hand-edit generated client files; regenerate after public backend changes.
- Preserve the existing `detail + request_id` error envelope and render Excel
  validation issues by worksheet, row, column, field, and message.
- Do not add a legacy migration page, new permission, database migration, CSV,
  `.xls`/`.xlsm`, or background jobs.

## Acceptance Criteria

- [ ] Authorized inventory operators can download the standard template,
  submit one valid XLSX from either document page, see the created document
  count, and see the refreshed list.
- [ ] Invalid file extension or a file larger than 10 MiB is blocked in the
  browser; backend 422 issues render in a readable error table.
- [ ] A raw page rejects finished-shipment rows and a shipment page rejects raw
  rows with positional Excel issues and no partial writes.
- [ ] Ledger exports apply all filters available on the corresponding page,
  including shipment receiving unit and document number.
- [ ] Viewer and operator permission states expose only the commands allowed by
  their existing grants.
- [ ] Generated client output, focused tests, lint, type/build, and browser
  regression checks are reviewed and pass or have a concrete environment
  blocker recorded.

## Notes

- The existing untracked `dump.rdb` is outside this task and must remain
  untouched.
