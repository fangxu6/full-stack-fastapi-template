# Implementation Plan: Trellis workflow parity

## Checklist

1. Establish baseline:
   - Read `.trellis/workflow.md`.
   - Re-check local runtime evidence in `compose.yml`, `compose.override.yml`, `frontend/playwright.config.ts`, `scripts/test.sh`, and backend docs.
   - Confirm whether `.trellis/scripts/spec_wiki.py` exists yet.
2. Draft workflow edits:
   - Add `grill-with-docs` routing for complex/risky planning.
   - Add `e2e-api-tests.md` to planning artifact rules for API-facing or cross-layer complex tasks.
   - Add local E2E validation guidance using backend `8000`, frontend `5173`, Docker Compose, and `/api/v1/utils/health-check/`.
   - Add `spec_wiki.py index/lint/log` only if the script exists or is introduced in the helper-script task.
3. Preserve breadcrumb invariants:
   - Update `[workflow-state:planning]` and `[workflow-state:planning-inline]` if Phase 1 required behavior changes.
   - Update `[workflow-state:in_progress]` and `[workflow-state:in_progress-inline]` if Phase 2 check behavior changes.
   - Ensure detailed walkthrough text and breadcrumb text agree.
4. Avoid JSE leakage:
   - Search the edited workflow for `9000`, `pm2`, `fastapi-app`, `PMS`, `Tooling`, `JSE`, `5174`, and reject/replace unless intentionally documented as "do not copy".
5. Validate:
   - `python ./.trellis/scripts/get_context.py --mode phase`
   - `python ./.trellis/scripts/get_context.py --mode phase --step 1.1`
   - `python ./.trellis/scripts/get_context.py --mode phase --step 2.2`
   - If `spec_wiki.py` is present: `python ./.trellis/scripts/spec_wiki.py index`
   - If `spec_wiki.py` is present: `python ./.trellis/scripts/spec_wiki.py lint`
   - `git diff --check -- .trellis/workflow.md`
6. Review diff:
   - Confirm only workflow/task artifacts and explicitly approved spec catalog files changed.
   - Confirm no application code changed.

## Risk Points

- Making `grill-with-docs` mandatory for every small task would slow the workflow down; it should be scoped to complex/risky work.
- Copying `9000`/pm2 from `.trellis-other` would be wrong for this project.
- Referencing `spec_wiki.py` before importing it could create broken workflow instructions; gate that text on script availability.
- Adding a required artifact in detailed Phase 1 without adding it to breadcrumb blocks can make agents skip it.

## Stop Gate

The user reviewed the plan and requested implementation on 2026-07-22.

## Completed Validation

- Added project-local `.trellis/scripts/spec_wiki.py` with `index`, `lint`, and
  append-only `log` commands. The generated file inventory uses marker bounds
  so the existing hand-maintained catalog content remains intact.
- Added `.trellis/spec/templates/e2e-api-tests-template.md` and linked it from
  the template index.
- Updated workflow planning, execution, quality, and spec-update rules plus
  the matching normal and Codex-inline breadcrumbs.
- `python .trellis/tests/test_spec_wiki.py` passed: 5 tests.
- `python ./.trellis/scripts/spec_wiki.py index --check` passed.
- `python ./.trellis/scripts/spec_wiki.py lint` passed with 0 errors and 0
  warnings.
- `get_context.py --mode phase`, `--step 1.1`, and `--step 2.2` parsed the
  updated workflow successfully.
- `git diff --check` passed. The workflow contains no imported `9000`, pm2,
  `fastapi-app`, `PMS`, `Tooling`, `JSE`, or `5174` runtime assumption.
