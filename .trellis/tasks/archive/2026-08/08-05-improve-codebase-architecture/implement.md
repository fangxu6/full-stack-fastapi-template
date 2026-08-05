# Architecture review execution plan

## Current phase

Implementation and quality verification are complete. The work is ready for
the Phase 3.4 work commit and task archive.

## Completed planning steps

1. Inspect recent history, `CONTEXT.md`, relevant ADRs, architecture sources,
   callers, implementations, and tests.
2. Record only evidence-backed candidates that improve depth, locality,
   leverage, or testability.
3. Write and expose one timestamped HTML report outside the repository.
4. Ask the user to select one candidate.
5. Run the grilling decision tree for the selected candidate and update the
   task PRD/design with the resulting scope before any implementation request.

These planning steps are complete for the current candidate.

## Selected Candidate Steps

1. Load the frontend pre-development guidelines before editing.
2. Replace the correction page's inline permission query with
   `myPermissionsQueryOptions`.
3. Add the corrections-route one-request assertion to the existing permission
   guard Playwright spec.
4. Run the focused permission spec, frontend build, frontend lint, and
   `git diff --check`; review any lint write diff.
5. Confirm only the planned page, test, and task artifacts changed.

The deferred route/menu metadata consolidation is tracked separately in
`deferred-iterations.md` and did not enter this implementation.

## Validation

- Confirm the report exists at an absolute OS temp path.
- Confirm the report contains files, problem, solution, benefits, strength,
  before/after diagrams, and a top recommendation for every candidate.
- From `frontend/`: `bun test src/app/permissions.test.ts src/app/router/guards.test.ts`.
- From `frontend/`: `bunx playwright test tests/permission-guards.spec.ts --no-deps`.
- From `frontend/`: `bun run build`.
- From `frontend/`: `bun run lint`; review its write diff.
- From the repository root: `python hooks/run_quality_hooks.py --json` and
  `git diff --check`.

## Validation Evidence

- Bun unit tests: 5/5 passed.
- Permission guard E2E: 8/8 passed, including the corrections-page regression.
- Frontend build passed.
- Frontend lint passed; only the planned import formatting was applied, with
  an informational Biome schema-version mismatch.
- Project quality hooks passed the frontend component policy and skipped the
  backend policy because no backend files changed.
- The default Playwright command was attempted, but its setup dependency timed
  out waiting for the login API before target tests ran. The target spec mocks
  its required API paths, so `--no-deps` is the relevant isolated command.
- Confirm no production files or dependencies changed.
- `git diff --check`

## Rollback

Delete only the temporary report if it is no longer needed. Keep the Trellis
planning artifacts and do not revert unrelated user changes.
