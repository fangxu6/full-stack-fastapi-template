# Implementation Record: Frontend Query Retry Policy

## Completed Changes

Implemented in commit `af11708`:

- Added `frontend/src/app/query-retry.ts` with safe-method classification,
  transient-status filtering, cancellation guards, bounded `Retry-After`
  parsing, and two-step backoff.
- Added `frontend/src/app/query-retry.test.ts` covering retry count/status,
  safe methods, cancellation, network failures, both header formats, invalid
  headers, and 429 interception.
- Registered the policy on the shared QueryClient and the 429 interceptor in
  `frontend/src/main.tsx`.
- Updated frontend state-management/quality specs and quality-hook coverage.

## Validation Evidence

- `cd frontend && bun test src/app/query-retry.test.ts` -> 3 passed, 0 failed,
  29 assertions.
- TanStack Query v5 documentation confirms the function signatures and
  `failureCount` retry semantics used by the implementation.
- The existing scheduler `retry: false` overrides and mutation defaults remain
  in source; generated client and backend files are unchanged.

## Remaining Quality Gate

Completed for this task refresh:

- `python .trellis/scripts/task.py validate .trellis/tasks/08-02-frontend-query-retry-policy` -> 3 implement and 3 check context entries valid.
- `python .trellis/scripts/spec_wiki.py lint` -> 0 errors, 0 warnings.
- `git diff --check` -> passed.
- `python hooks/run_quality_hooks.py --json` -> backend and frontend source
  hooks correctly skipped because this pass changed task artifacts only.
- `cd frontend && bun test src/app/query-retry.test.ts` -> 3 passed, 0 failed,
  29 assertions.
- `cd frontend && bun run build` -> TypeScript passed; Vite could not resolve
  the already-declared `@vitejs/plugin-react` because it is absent from the
  current `frontend/node_modules`. No dependency or lockfile change is in
  scope for this task.

A browser E2E test is not required for this transport-only policy; the focused
unit test exercises the retry decision and header boundary.

## Rollback

Revert the retry policy registration, interceptor, focused tests, and related
spec entries together. No database, API, generated-client, or deployment
rollback is needed.
