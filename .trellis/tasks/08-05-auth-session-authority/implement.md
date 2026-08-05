# Auth-session authority implementation plan

## Preconditions

1. Review `prd.md`, `design.md`, and `e2e-api-tests.md`.
2. Activate the task with:
   `rtk python3 ./.trellis/scripts/task.py start 08-05-auth-session-authority`.
3. Load the backend pre-development rules before editing.

## Ordered changes

1. Add `backend/app/modules/auth/__init__.py` and
   `backend/app/modules/auth/session.py` with the four approved typed
   functions and existing `AuthenticationError` behavior.
2. Move access-session persistence and validation policy out of
   `backend/app/api/dependencies/auth.py` and keep only dependency wiring,
   request state, actor kind, and superuser checks there.
3. Update `backend/app/services/auth.py` so credential authentication remains
   local while access-token issuance and logout delegate to the new module.
4. Update every `revoke_all_user_sessions` caller in
   `backend/app/services/user.py` and `backend/app/services/auth.py`.
5. Add focused module tests at
   `backend/tests/modules/auth/test_session.py`.
6. Search for old access-session logic and imports; confirm no production
   caller still queries or updates `AuthSession` directly outside the new
   module.

## Validation

From the repository root, using the isolated test database required by the
backend spec:

```bash
cd backend && POSTGRES_DB=aiadmin_test uv run pytest \
  tests/modules/auth/test_session.py \
  tests/api/routes/test_login.py \
  tests/api/routes/test_users.py
```

```bash
cd backend && bash scripts/lint.sh
git diff --check
```

Run the API cases in `e2e-api-tests.md` against an isolated environment if the
local backend is available. No frontend build or client regeneration is needed
because the API contract is unchanged.

## Validation Notes

- `POSTGRES_DB=aiadmin_test uv run pytest tests/modules/auth/test_session.py tests/api/routes/test_login.py tests/api/routes/test_users.py`: 55 passed.
- `POSTGRES_DB=aiadmin_test uv run pytest tests`: 351 passed, 2 skipped, 3 warnings.
- `cd backend && bash scripts/lint.sh`: passed; mypy, ty, Ruff, and format checks passed.
- `git diff --check`: passed.
- `python3 -m py_compile` for all changed Python files: passed.
- `task.py validate 08-05-auth-session-authority`: passed.
- The local API E2E attempt was blocked because `127.0.0.1:8000` was not running; the same flows are covered by the TestClient route suite above.

## Review gates

- No `commit()` or `rollback()` appears in `modules/auth/session.py`.
- `AuthSession` production imports and direct queries are confined to the new
  module and the unchanged model definition.
- Existing 401 behavior and logout idempotency remain covered.
- Password-token, password-hash, and recovery-email paths are unchanged.
- No migration, schema, OpenAPI, dependency, or frontend-client diff exists.

## Rollback

If module tests or route behavior fail, restore only the auth-session imports
and delegation calls, remove the new module/tests, and leave the existing
model, migrations, and unrelated worktree changes untouched.
