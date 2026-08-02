# Inventory Excel Frontend Acceptance Matrix

| ID | Flow | Expected result |
| --- | --- | --- |
| E2E-001 | Raw-page standard import with a raw workbook | 201, refreshed raw list, created-count confirmation |
| E2E-002 | Shipment-page import with a raw row | 422 issue for the `单据类型` cell and no persisted document |
| E2E-003 | Export with date, processing unit, document number, and receiving unit | XLSX request carries all filters and excludes nonmatching ledger rows |
| E2E-004 | Client chooses a non-XLSX or over-limit file | Upload is blocked before network submission |
| E2E-005 | Server returns Excel 422 issues | Dialog presents worksheet/row/column/field/message values |
| E2E-006 | Permission variants | Manage grants show import/template; ledger-read shows export; no grant shows neither |
