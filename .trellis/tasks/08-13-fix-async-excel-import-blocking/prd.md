# Fix Blocking Async Excel Import Endpoints

## Goal

Keep XLSX import requests from running synchronous workbook parsing and SQLModel operations inside the FastAPI event loop.

## Confirmed Facts

- `backend/app/modules/inventory/router.py` declares both import operations as `async def`, then invokes synchronous workbook parsing and SQLModel transaction work in `import_document_workbook()` and `import_legacy_workbooks()`.
- The application uses synchronous SQLModel sessions. FastAPI runs synchronous path operations in its threadpool, which is sufficient for this bounded remediation.
- The import handlers currently use `await UploadFile.read()` through `_read_xlsx_upload()`. A synchronous handler must instead read the uploaded file synchronously while preserving chunked reading, the 10 MiB limit, and `ExcelValidationError` behavior.
- `backend/tests/api/routes/test_inventory.py` already covers document-import success, rollback, input validation, legacy-import success, and legacy row-error responses.

## Requirements

- Convert both inventory XLSX import path operations and their upload reader to synchronous functions while preserving upload parsing, validation, transaction, permission, response model, and status-code behavior.
- Read `UploadFile.file` in bounded chunks; preserve the existing filename extension check and 10 MiB source-size limit.
- Add a narrow regression test that verifies both import handlers are synchronous functions. Reuse the existing endpoint tests for public behavior.
- Do not introduce an executor, Asyncer, a task queue, a new API contract, or frontend client regeneration.

## Acceptance Criteria

- [ ] `import_documents_from_excel` and `import_legacy_workbooks_from_excel` are declared with `def`, not `async def`.
- [ ] The synchronous upload reader preserves extension validation and the 10 MiB input limit.
- [ ] Existing document/legacy multipart import, rollback, and error-envelope tests still pass; generated OpenAPI has no contract diff.
- [ ] The focused structural regression test and backend lint/type checks pass.

## Out Of Scope

- Background import jobs, progress reporting, concurrency limits, executor tuning, and changes to workbook parsing or SQLModel transaction rules.
- The separate `Annotated` and Ellipsis cleanup tasks.

## Key Decision

- Use FastAPI's native synchronous path-operation threadpool. This removes synchronous parsing/database work from the event loop without adding a dependency or changing client-visible behavior.

