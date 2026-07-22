# Inventory Unit Remote Search Implementation Plan

1. Add a feature-local remote-unit Select hook around the existing processing
   and receiving unit page readers. Define 20-row initial/search requests,
   300 ms debounce, active-state scope, query keys, selected-option retention,
   and loading/error/empty output.
2. Replace the fixed 100-row query state in `InventoryDocumentsPage` with the
   hook for both historical filters. Replace the editor modal's fixed query
   state with active-only hook instances.
3. Extend the inventory Playwright coverage for a unit beyond the initial
   result window and verify filtering and document entry can select it. Keep
   E2E execution isolated from the development database.
4. Add the reusable server-backed Select guidance to the frontend spec. Run
   Biome CI, production build, focused backend inventory tests, and the
   applicable UI test before completion.

## Risk Checks

- Do not edit `frontend/src/client/**`; `frontend/src/features/inventory/api.ts`
  is the approved feature-local query wrapper.
- Avoid a generic `shared/*` Select abstraction because active scope and unit
  vocabulary are inventory-domain behavior.
- Confirm searches do not accidentally expose inactive units in write fields.

## Completed Validation

- Added `unit-select-options.ts` with a 20-row request limit, 300 ms debounce,
  domain-scoped query keys, remote option mapping, and selected options retained
  while the current session changes search terms.
- Replaced all four fixed `limit=100, skip=0` document unit loads. Historical
  filters omit `is_active`; editor fields request `is_active=true`.
- `bun test src/features/inventory/unit-select-options.test.ts` passed: 2 tests.
- Read-only Biome CI passed for all changed frontend source and Playwright files.
- `bun run build` passed.
- `POSTGRES_DB=aiadmin_test uv run pytest tests/api/routes/test_inventory.py`
  passed: 22 tests.
- The isolated Playwright test passed against a backend started with
  `POSTGRES_DB=aiadmin_test`. It constructs a target outside the newest 100
  units, then verifies filter and editor remote search request parameters and
  selection behavior.
- `git diff --check` and `task.py validate` passed.

## Accepted Scope Boundary

An existing document whose unit is not available in the hook's first server
page cannot be name-resolved from its ID because the current API exposes no
single-unit lookup or document-side unit label. Adding that backend contract is
outside this task; this implementation retains labels for options selected
during the current session and does not expand the API boundary.
