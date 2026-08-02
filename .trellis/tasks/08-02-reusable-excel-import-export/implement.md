# Reusable Excel Import/Export Implementation Plan

1. Add `defusedxml` and implement the focused `app.core.excel` helper with
   typed locations/issues, bounded XLSX loading, alias-driven DTO validation,
   and alias-driven workbook rendering.
2. Add core tests before integrating inventory, including workbook safety and
   output header/order checks.
3. Add inventory Excel DTOs, structured import/response schemas, and the
   semantic 422 exception path.
4. Implement standard flattened document import with active-name resolution,
   group consistency checks, nested validation attempts, and all-or-nothing
   persistence through the existing inventory service.
5. Refactor legacy import internals to named byte sources while preserving the
   path-based CLI wrapper; adapt legacy parsing failures to structured issues.
6. Add full ledger export query/DTO and the four inventory routes with existing
   permission dependencies and streaming XLSX responses.
7. Add focused core, service, and route tests; regenerate the frontend client;
   run backend lint/type checks and the E2E API cases.
8. Record the durable Excel boundary in Trellis backend specifications, update
   the spec index, then commit only task-scoped source, generated client, and
   documentation changes.

## Rollback

- The feature adds routes and source modules only; no migration is required.
- Revert the commit to remove all endpoints and helpers. Existing CLI behavior
  remains preserved by its compatibility wrapper.

## Completed

- Added the reusable core XLSX reader/writer, bounded upload parsing, macro
  rejection, structured issues, and direct `defusedxml` dependency.
- Added inventory DTOs, standard document import, byte-backed historical
  import, template/ledger routes, Chinese ledger output, and generated client
  updates without a migration or new RBAC grant.
- Preserved the legacy CLI path wrapper and restored any pre-existing audit
  actor after its explicitly owned transaction completes.

## Verification (2026-08-02)

- `POSTGRES_DB=aiadmin_test uv run --project backend pytest backend/tests/core/test_excel.py backend/tests/modules/inventory/test_importer.py backend/tests/api/routes/test_inventory.py`
  - 51 passed, 2 skipped because the optional real legacy workbook fixtures are
    absent locally.
- `bash -lc 'cd backend && ./scripts/lint.sh'`
  - mypy, ty, Ruff check, and Ruff format all passed.
- `bash ./scripts/generate-client.sh`
  - OpenAPI client regenerated and Biome passed.
