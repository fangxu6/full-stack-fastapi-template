# Reusable Excel Deferred Iterations

## Purpose

Keep future spreadsheet workflows visible without expanding the current
backend-only delivery.

## Traceability Rules

- Deferred items do not affect current acceptance criteria.
- Each item requires its own Trellis task before implementation.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Frontend upload/download and issue-highlighting workflow | Current scope is backend REST only | Stable import/export OpenAPI contracts | Feature UI, generated-client consumers, browser E2E |
| D-002 | CSV, `.xls`, `.xlsm`, versioned templates, and configurable columns | The fixed XLSX contract is the smallest safe reusable baseline | Core XLSX usage evidence | Format policy, compatibility matrix, security tests |
| D-003 | Asynchronous large-file batches and error-annotated workbooks | Current limit is synchronous 10 MiB / 10,000 rows | Measured need beyond current limit | Batch persistence, storage, progress API, UI remediation |

## Remaining Work In Current Scope

- Implement and verify the core XLSX contract and inventory APIs described in
  `prd.md`, `design.md`, `implement.md`, and `e2e-api-tests.md`.
