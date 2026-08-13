# Remove Ellipsis from FastAPI File Parameters

## Goal

Remove deprecated Ellipsis defaults from the inventory XLSX upload parameters while preserving each endpoint's required multipart upload contract.

## Confirmed Facts

- `backend/app/modules/inventory/router.py` declares three target parameters: `workbook` for `POST /api/v1/inventory/excel/imports/documents`, plus `raw_workbook` and `finished_workbook` for `POST /api/v1/inventory/excel/imports/legacy`.
- All three use `UploadFile = File(...)`; the router already imports `Annotated`.
- The current success paths are covered in `backend/tests/api/routes/test_inventory.py`; missing-file validation is not directly asserted.
- The application wraps FastAPI validation errors with the established `detail` and `request_id` response contract.

## Requirements

- Replace only the three target declarations with `Annotated[UploadFile, File()]`.
- Preserve route paths, parameter names, authorization, response models, status codes, multipart field names, requiredness, and OpenAPI request-body semantics.
- Add focused regression coverage proving each required upload field rejects an omitted multipart file with `422` and the standard validation error shape.

## Out of Scope

- Migrating non-file FastAPI parameters or other routes to `Annotated`.
- Changing XLSX content validation, import behavior, permission rules, or generated frontend client code.
- OpenAPI client regeneration: this type-annotation-only migration preserves the public request contract.

## Acceptance Criteria

- [x] `backend/app/modules/inventory/router.py` has no target `File(...)` Ellipsis defaults.
- [x] The documents import rejects a request without `workbook` with `422`, `detail`, and `request_id`.
- [x] The legacy import rejects requests missing either `raw_workbook` or `finished_workbook` with the same validation contract.
- [x] Focused inventory route tests and the backend lint/type/format gate pass.

## Key Decision

- This is a lightweight PRD-only task. The smallest correct change is the three signature annotations plus a single parameterized missing-file contract test; no new abstraction, migration, or cross-layer artifact is warranted.
