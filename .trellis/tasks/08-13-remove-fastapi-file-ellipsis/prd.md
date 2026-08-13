# Remove Ellipsis from FastAPI File Parameters

## Goal

Remove deprecated Ellipsis defaults from required FastAPI file parameters while preserving required multipart upload semantics.

## Requirements

- Replace each targeted `UploadFile = File(...)` declaration with the equivalent `Annotated[UploadFile, File()]` form.
- Keep the parameters required, preserve endpoint names and OpenAPI request schemas, and avoid unrelated parameter migrations.
- Scope is limited to the inventory XLSX upload endpoints.

## Acceptance Criteria

- [ ] No targeted upload parameter uses `File(...)` with Ellipsis.
- [ ] Missing required workbook uploads still produce FastAPI validation errors.
- [ ] Focused endpoint tests and lint/type checks pass.

