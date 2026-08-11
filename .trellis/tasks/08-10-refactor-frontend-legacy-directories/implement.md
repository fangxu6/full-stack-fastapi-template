# Implementation Plan: Frontend Legacy Directory Refactor

## 1. Establish The Final Tree

- Move shadcn/ui primitives to `shared/components/ui` without changing their
  implementations.
- Move the theme provider to `shared/components/theme/ThemeProvider.tsx`.
- Replace the two shared feedback skeleton re-exports with their moved Pending
  implementations, then remove `components/Pending`.
- Move generic hooks to `shared/hooks`, `useAuth` to `platform/auth/hooks`,
  and merge the two utility files into `shared/utils/index.ts`.
- Remove the now-empty `components`, `hooks`, and `lib` roots and root
  `utils.ts` only after all imports resolve.

## 2. Rewrite Imports And Tooling

- Rewrite every frontend import, including imports inside shadcn primitives and
  `main.tsx`, to the final aliases or final relative paths.
- Update `components.json`, `biome.json`, frontend quality-hook constants, and
  focused quality-hook tests for the final vendor-style primitive location.
- Keep generated client and route-tree files untouched.

## 3. Reconcile Active Guidance

- Update active Trellis frontend specs, `frontend/ARCHITECTURE.md`,
  `frontend/CODING_STANDARDS.md`, and `frontend/README.md` to remove the
  retired structure and preserve current ownership rules.
- Update the frontend index's current-reality wording so it no longer says
  legacy roots remain after this task removes them.

## 4. Verify

Run from the repository root unless noted otherwise:

```powershell
rg -n "@/(components|hooks|lib|utils)|src/(components|hooks|lib)|src/utils\.ts" frontend hooks .trellis/spec
Push-Location frontend; bunx @biomejs/biome@2.3.14 ci --no-errors-on-unmatched --files-ignore-unknown=true src biome.json components.json; Pop-Location
Push-Location frontend; bun run build; Pop-Location
uv run pytest hooks/tests/test_quality_hooks.py -q
uv run python hooks/run_quality_hooks.py --hook frontend-component-policy
git diff --check
```

Run `Push-Location frontend; bunx playwright test; Pop-Location` against the
documented local stack. If that environment cannot be started, record the
concrete blocker after attempting it; do not treat an unstarted browser suite
as a passing result.

### Verification Record (2026-08-11)

- The scoped read-only Biome command passes. The unpinned command resolves
  Biome 2.4.16 while `biome.json` declares the 2.3.14 schema and also scans
  unrelated generated/runtime artifacts, so it is not used as task evidence.
- With the local backend at `8000`, Playwright runs all 78 tests using the
  existing `http://localhost:5173` frontend origin and `NO_PROXY` for loopback:
  65 pass and 13 fail. The failures require services or data outside this task
  (Mailcatcher at `localhost:1080`, inventory fixtures, and scheduler
  permissions), plus pre-existing toast/form display assertions. Serial reruns
  confirm the affected admin suite is 12/13 and user-settings suite is 12/15;
  all three theme tests pass. `useCustomToast` and the `sonner` primitive are
  byte-identical moves, while the failing components changed only import paths.
  Those failures are owned by
  [08-11-reconcile-frontend-e2e-baseline](../08-11-reconcile-frontend-e2e-baseline/prd.md)
  and do not gate this path-only migration task.

## 5. Review And Rollback

- Review the final tree, alias configuration, policy paths, and stale-reference
  search before committing.
- Revert the moved source, import rewrites, tooling changes, and docs together
  if validation reveals a compatibility failure.
- Keep unrelated user worktree changes unstaged and untouched.
