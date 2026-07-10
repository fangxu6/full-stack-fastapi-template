# Keep items on lightweight CRUD implementation plan

## Steps

1. Write/update failing tests that assert `/api/v1/items/*` is present and `/api/v1/modules/items/*` is absent.
2. Restore `api/routes/items.py`, `services/item.py`, and `crud/item.py` as the item CRUD chain.
3. Remove item-owned module routing and any imports from `app.modules.items`.
4. Regenerate the frontend OpenAPI client.
5. Update backend architecture/Trellis specs for the simple-CRUD-first rule.
6. Run focused backend tests, frontend type/build checks as needed, changed-file lint/type checks, and `git diff --check`.

## Validation Commands

- `cd backend && uv run pytest tests/crud/test_item.py tests/api/routes/test_items.py tests/api/routes/test_users.py`
- `cd backend && uv run mypy app/api/routes/items.py app/services/item.py app/crud/item.py tests/crud/test_item.py tests/api/routes/test_items.py tests/utils/item.py`
- `cd backend && uv run ty check app/api/routes/items.py app/services/item.py app/crud/item.py tests/crud/test_item.py tests/api/routes/test_items.py tests/utils/item.py`
- `cd backend && uv run ruff check app/api/routes/items.py app/services/item.py app/crud/item.py tests/crud/test_item.py tests/api/routes/test_items.py tests/utils/item.py`
- `cd backend && uv run ruff format app/api/routes/items.py app/services/item.py app/crud/item.py tests/crud/test_item.py tests/api/routes/test_items.py tests/utils/item.py --check`
- `bash ./scripts/generate-client.sh` or an equivalent Git Bash invocation on Windows
- `cd frontend && bun run build`
