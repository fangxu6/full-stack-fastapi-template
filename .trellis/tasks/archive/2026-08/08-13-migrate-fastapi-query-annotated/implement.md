# Implementation Plan

1. Read the backend route/type-safety and quality specs before editing.
2. Add `Annotated` imports only where needed in the four target routers.
3. Convert each legacy `Query` default to `Annotated` metadata, preserving all
   existing defaults and constraints exactly.
4. Add the AST regression test for the four target files.
5. Run the focused route tests and the structural test with the isolated test
   environment.
6. Generate OpenAPI/client artifacts through the repository script, inspect the
   diff, and retain generated files only if the generator reports a legitimate
   contract change. Expected result: no generated diff.
7. Run the backend quality gate from `backend/` (`mypy`, `ty`, Ruff, and format
   check) plus `git diff --check`.
8. Review the final diff for scope drift, then commit the code and test changes
   as one coherent work commit. Archive and journal are separate finish-work
   commits.

## Risky Points

- Required query parameters must not gain a default.
- Optional query defaults must stay outside `Query` metadata.
- Do not mass-format unrelated backend files.

## Validation Commands

```powershell
$env:POSTGRES_DB = 'aiadmin_test'
bash -lc 'cd backend && uv run pytest tests/api/routes/test_items.py tests/api/routes/test_inventory.py tests/api/routes/test_scheduler.py tests/api/test_fastapi_query_annotations.py'
bash ./scripts/generate-client.sh
bash -lc 'cd backend && ./scripts/lint.sh'
git diff --check
```
