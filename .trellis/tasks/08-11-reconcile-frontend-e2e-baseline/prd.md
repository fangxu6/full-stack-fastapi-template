# Reconcile frontend E2E baseline failures

## Goal

Reconcile the 13 failing frontend Playwright cases caused by runtime services, fixtures, permissions, or stale browser assertions after the legacy-directory migration.

## Requirements

1. Reproduce and classify all 13 baseline failures from the 2026-08-11
   Playwright run under an isolated local test environment.
2. Make the suite deterministic by providing the required mail sink, inventory
   fixtures, scheduler permissions, and test data, or by correcting assertions
   that no longer match the established product contract.
3. Preserve production behavior and the completed legacy-directory migration;
   do not change UI behavior merely to satisfy an E2E assertion.
4. Record the required local test services and invocation so the complete
   Playwright suite can be rerun consistently without Docker.

## Acceptance Criteria

- [ ] The Mailcatcher-dependent reset-password cases run against an available
      isolated mail sink and pass.
- [ ] Inventory and scheduler cases create or select their required fixtures
      and permissions deterministically.
- [ ] Admin and user-settings browser assertions match the current documented
      success and form-display contracts.
- [ ] `bunx playwright test` passes all 78 cases in the documented isolated
      local environment.
- [ ] The parent legacy-directory task's moved implementations and ownership
      boundaries remain unchanged except where a proven E2E defect requires a
      narrowly scoped correction.

## Constraints

- This is the owner of the 13 full-suite failures observed while validating
  `08-10-refactor-frontend-legacy-directories`; it is not a reason to reopen
  the completed source-path migration.
- Plan this as a complex task before implementation because it spans browser
  tests, runtime services, fixtures, permissions, and product assertions.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
