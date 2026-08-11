# SchedulerRun Terminal Ownership Implementation

## Implementation Checklist

1. Change `finish_outcome()` to lock the run row and require the expected
   execution lease before applying a terminal outcome.
2. Capture the non-null claim lease in `execute_run()` and pass it to
   `finish_outcome()`; retain the existing early return for rejected results.
3. Update direct lifecycle callers and the scheduler state transition matrix.
4. Add reclaim-versus-late-result and stale-alert regressions to the scheduler
   test module.

## Validation

1. Run the focused scheduler tests with `POSTGRES_DB` set to an isolated
   database ending in `_test` or `_pytest`.
2. Run `bash -lc 'cd backend && ./scripts/lint.sh'`.
3. Run `git diff --check` and inspect the staged task, code, test, and matrix
   changes before committing.

## Rollback

Revert the implementation commit. There is no migration, generated client, or
external deployment state to reverse.
