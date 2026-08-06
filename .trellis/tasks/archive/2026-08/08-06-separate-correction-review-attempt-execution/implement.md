# Implementation: Separate Correction Review From Attempt Execution

## Ordered Checklist

1. Inventory all correction service callers, imports, tests, and private helper
   dependencies; record the exact function move set.
2. Add `backend/app/modules/inventory/correction_attempts.py` with the existing
   attempt exception, lease/claim/apply/finalize functions, and their terminal
   helpers. Preserve logic and signatures.
3. Remove the moved attempt code from `correction_service.py`, retaining the
   request/review/recovery API and only the shared helpers it still needs.
4. Update `scheduled_tasks.py` to import attempt functions and
   `CorrectionApplicationError` from `correction_attempts` without changing
   session, audit actor, commit, rollback, or Celery behavior.
5. Update/add focused tests to assert the new module owns attempt behavior and
   the route/task callers retain their existing observable contracts.
6. Run focused correction and scheduler tests, then the backend lint/type
   gate. Fix only regressions caused by this split.
7. Review the final diff for API/schema/database/queue churn and update the
   backend spec only if the new module boundary is a durable executable
   convention.

## Validation Commands

From `backend/`:

```powershell
$env:POSTGRES_DB = "aiadmin_test"
uv run pytest tests/api/routes/test_inventory_corrections.py tests/modules/scheduler
bash scripts/lint.sh
```

Also run `git diff --check`, inspect changed-file scope, and report any full
suite failures separately from scheduler/correction failures.

## Review Gates

- `correction_attempts.py` owns all lease/claim/application/terminal attempt
  transitions and no request route imports it.
- `documents.py` remains the only module that changes inventory documents and
  ledger effects.
- No deepened module commits or rolls back.
- A failed item still rolls back its mutation and finalizes in a separate
  short transaction; one failed item does not abort the scan.
- Stale, terminal, and already-completed attempts remain no-ops where they
  were no-ops before.
- Only the intended source, test, task-artifact, and optional spec files are
  changed.

## Validation Record

- Passed: `uv run pytest tests/api/routes/test_inventory_corrections.py
  tests/modules/scheduler` (`57 passed`).
- Passed: `uv run pytest tests/modules/inventory/test_documents.py
  tests/api/routes/test_inventory_corrections.py` (`7 passed`).
- Passed: `bash -lc 'cd backend && ./scripts/lint.sh'` (mypy, ty, Ruff,
  formatting).
- `tests/modules/inventory` was also attempted (`30 passed, 2 failed, 2
  skipped`). The failures are pre-existing shared `aiadmin_test` data
  contamination in `test_documents.py` and `test_importer.py`; they do not
  involve the changed modules and the focused document/correction tests pass.
