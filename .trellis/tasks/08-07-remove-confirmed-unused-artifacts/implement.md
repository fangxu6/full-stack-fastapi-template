# Implementation Plan: Remove Confirmed Unused Repository Artifacts

1. Activate the reviewed Trellis task.
2. Delete the five architecture review snapshots, root OpenAPI snapshot, empty
   logging shim, duplicate test readiness module, and duplicate readiness test.
3. Update `backend/scripts/tests-start.sh` to call
   `python app/backend_pre_start.py`.
4. Remove the five unused frontend dependencies from `frontend/package.json`.
5. Regenerate `bun.lock` with the existing workspace package manager.
6. Verify deleted-file and dependency references with `rg`, while checking that
   cache, retained UI, PM2, and frontend OpenAPI paths remain present.
7. Run focused backend readiness tests, the PM2 wrapper test, frontend build,
   and diff/status checks.

## Validation Commands

```bash
cd backend && uv run pytest tests/scripts/test_backend_pre_start.py
node --test scripts/pm2-json-prefix.test.cjs
bun install --lockfile-only
bun --cwd frontend run build
git diff --check
git status --short
```

## Review Gates

- Confirm the deletion list matches the user-approved boundary before running
  destructive file operations.
- Confirm `backend/app/core/cache.py`, the four retained UI files,
  `ecosystem.config.js`, `scripts/pm2-json-prefix.cjs`, and
  `frontend/openapi-ts.config.ts` are unchanged and present.
- Do not commit unrelated generated or ignored files.
