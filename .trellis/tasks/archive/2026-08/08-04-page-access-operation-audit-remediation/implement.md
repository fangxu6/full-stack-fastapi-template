# IAM audit remediation implementation plan

## Ordered checklist

1. Add a locked role-read option in the IAM repository, preserving the current
   non-locking read behavior for callers that do not opt in.
2. Route all existing-role IAM mutation service entry points through that lock
   before they inspect state or write audit evidence.
3. Add an IAM-local unified 422 error and derive an actual-change dictionary
   in `update_role()`. Raise before any write when no supplied value differs.
4. Add regression tests before production edits:
   - two-session role-permission replacement serialization and audit snapshot;
   - empty PATCH 422 with no role/audit mutation;
   - same-value PATCH 422 with no role/audit mutation;
   - real PATCH regression for one semantic event.
5. Run the new tests red, make the smallest production changes to pass, then
   run focused IAM/audit/Celery-registration tests and the backend lint gate.
6. Inspect the final diff and run `git diff --check`. Do not add a migration,
   generated frontend output, API reader, or unrelated refactor.

## Validation commands

Run from the repository root using the isolated database:

```powershell
$env:POSTGRES_DB = 'aiadmin_test'
Set-Location backend
uv run pytest -q tests/modules/iam/test_iam_service.py tests/api/routes/test_iam_audit.py tests/modules/audit tests/core/test_celery.py
bash ./scripts/lint.sh
```

The focused audit/IAM subset must pass. If the existing production-mode Celery
subprocess failures recur because their copied environment lacks
`REDIS_PASSWORD`, record that unrelated blocker separately and retain the
passing focused audit/IAM result.

## Rollback

The change has no schema migration. Reverting the application commit restores
the prior no-op PATCH behavior and removes the service-level row lock; no
stored audit rows require migration or cleanup.

## Execution evidence

- TDD regression run before the production edits demonstrated the original
  failures: concurrent replacements retained both requested permission links,
  and empty or same-value PATCH returned 200.
- New regression tests passed after the implementation: `3 passed`.
- Focused IAM, audit, and Celery-registration suite passed on
  `aiadmin_clean_pytest`: `16 passed`.
- `bash ./scripts/lint.sh` passed its mypy, ty, Ruff, and formatting checks.
- A local isolated backend was started with `POSTGRES_DB=aiadmin_test`.
  Health returned 200; authenticated create-role followed by empty PATCH
  returned the expected 422 contract (`E2E_EMPTY_PATCH_422_OK`). The server
  was stopped after the check.
- The initial full suite exposed five test-only stale assumptions: a fixed
  write-route count, a production-mode subprocess environment with no test
  Redis password, and an importer assertion that did not identify its own
  import batch. Those regressions were reproduced in a new
  `aiadmin_clean_pytest` database, corrected without changing production code,
  and their focused rerun passed: `5 passed`.
- Final full pytest on `aiadmin_clean_pytest` passed: `318 passed, 2 skipped`.
- Final audit review added a regression for a mixed PATCH containing an
  unchanged `is_active` plus a renamed role. The event now derives
  `changed_fields` from the actual-change dictionary, so the same-value state
  field is not misrepresented as a semantic change.
