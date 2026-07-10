# Modularize backend items boundary implementation plan

## Steps

1. Write failing tests for item no-commit persistence helpers and module service persistence.
2. Add `backend/app/modules/items/repository.py`, `service.py`, and package exports.
3. Change `api/routes/items.py` or compatibility service imports so routes call module service behavior without public API changes.
4. Change `crud/item.py` to delegate to module repository without committing.
5. Update item test helpers and CRUD tests for explicit commit/service usage.
6. Add ADRs and update backend architecture/spec docs for the new pilot rule.
7. Compare OpenAPI output before/after implementation.
8. Run focused item tests, backend lint, and backend test suite.

## Validation Commands

- `cd backend && uv run pytest tests/crud/test_item.py tests/api/routes/test_items.py`
- `bash backend/scripts/lint.sh`
- `cd backend && bash scripts/test.sh`

## Rollback Points

- If OpenAPI differs unexpectedly, keep `api/routes/items.py` unchanged and revert only service/repository wiring.
- If no-commit item CRUD causes excessive blast radius, restore `crud.item` commit behavior and keep the new no-commit repository under `modules/items`.
