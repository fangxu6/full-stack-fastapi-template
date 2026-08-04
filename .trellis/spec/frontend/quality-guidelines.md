# Quality Guidelines

> Frontend review and regression guardrails for this repository.

---

## Overview

Frontend quality in this repo is mostly about preserving structural boundaries and generated-contract discipline while protecting core user states such as route access, empty states, and error handling.

---

## Required Patterns

- Keep route files thin.
- Keep shell, navigation, and guards in `app/*`.
- Keep domain pages in `platform/*` or `features/*`.
- Keep genuinely shared UI and helpers in `shared/*`.
- Use `@/` aliases and generated client types consistently.
- Keep Ant Design usage within the documented complex-component boundary in
  [Component Guidelines](./component-guidelines.md).
- Respect Biome exclusions and generated/vendor-style boundaries from
  [`frontend/biome.json`](../../../frontend/biome.json).
- `frontend/src/main.tsx` is the sole non-component bootstrap exception to the
  component-root policy; other non-route `.tsx` files must remain under an
  approved component root.

## Scenario: Thin Route AST Enforcement

### 1. Scope / Trigger

- Trigger: a changed, existing file under `frontend/src/routes/**`.
- The frontend quality hook delegates route-shape checks to
  `scripts/check-thin-routes.mjs`; deleted paths are skipped because they have
  no source left to validate.

### 2. Signature

```bash
bun scripts/check-thin-routes.mjs <route-file> [<route-file> ...]
```

The command writes JSON containing each checked file path and its violations.
The hook resolves Bun from `PATH` first and otherwise uses Bun's standard
user-local installation path, so non-interactive Git hooks retain the same
runtime as the frontend toolchain.

### 3. Contract

- Ordinary route entries may export `Route`, configure guards/search/head, and
  reference imported page components.
- Ordinary route entries must not declare a local PascalCase component or use
  an inline function for `component`, `errorComponent`, or
  `notFoundComponent`.
- `frontend/src/routes/__root.tsx` is the sole Router-shell exception for its
  existing framework callbacks; it is not a business-page placement location.

### 4. Validation And Error Matrix

| Condition | Result |
| --- | --- |
| Imported page component in an ordinary route | Pass |
| Local `function Dashboard()` or `const Dashboard = () => ...` | Fail |
| Inline `component: () => <Page />` | Fail |
| Existing root Router shell callbacks | Pass |
| Deleted route path | Skip |

### 5. Good / Base / Bad Cases

- Good: a route imports `DashboardPage` from `platform/dashboard/pages` and
  assigns it to `component`.
- Base: `__root.tsx` uses its documented Router shell callbacks.
- Bad: a route implements its page below `export const Route`.

### 6. Tests Required

- Unit-test the AST checker for imported pages, named local components, inline
  callbacks, and the root exception.
- Keep one inventory regression that scans every current `routes/**/*.tsx`
  entry. The hook validates only changed paths, so this baseline test prevents
  an untouched legacy route from escaping the policy indefinitely.
- Unit-test the Python hook with an inline route callback to prove it delegates
  to the checker.
- Run `python hooks/run_quality_hooks.py --json` and frontend type/Biome checks.

### 7. Wrong vs Correct

#### Wrong

```tsx
export const Route = createFileRoute("/reports")({
  component: () => <ReportsPage />,
})
```

#### Correct

```tsx
import { ReportsPage } from "@/platform/reports/pages/ReportsPage"

export const Route = createFileRoute("/reports")({
  component: ReportsPage,
})
```

---

## Forbidden Patterns

- Do not edit generated files directly:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`
  - `frontend/src/components/ui/**`
- Do not push page implementations back into `routes/*`.
- Do not use `shared/*` as a first-stop bucket for domain-specific code.
- Do not mass-format unrelated files while touching frontend code.
- Do not hand-write API types that already exist in the generated client.
- Do not introduce `@ant-design/pro-components` or migrate existing shadcn/ui
  flows to Ant Design without a task-specific design review.

---

## Cross-Layer Review Rules

- If backend schema changed, regenerate the frontend client.
- If route or permission behavior changed, verify route guards, navigation visibility, and redirect behavior together.
- If generated client output changed, verify consumers import generated services/types instead of recreating local API contracts.
- If route tree generation changed, verify route files remain thin and `frontend/src/routeTree.gen.ts` is generated output, not hand-edited business code.
- After `scripts/generate-client.sh` or a TanStack Router scan changes
  `frontend/src/client/**` or `frontend/src/routeTree.gen.ts`, review the diff
  and follow Workflow Phase 3.4: propose those files as the first, dedicated
  synchronization commit and wait for the existing one-shot confirmation.
  Do not add automatic commits to generators or hooks.
- If a page changed, check for regressions in:
  - empty state
  - error state
  - permission state
  - loading state
- If a UI flow changed, check success, failed mutation, pending/loading, and no-data states instead of only the happy path.
- If Ant Design components are introduced, verify they render correctly through
  the global `AntdProvider` in light, dark, and system theme modes.

---

## Current Reality vs Recommended Direction

### Current reality

- The repo already has thin routes and split page placement:
  - [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx)
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Guard and permission entrypoints are centralized:
  - [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)

### Recommended direction

- Use review pressure to stop future regressions back into route-heavy pages or overstuffed shared folders.
- Treat generated-client discipline and frontend boundary placement as part of the same quality gate.

---

## Minimum Validation Expectations

- Use `bun run lint` as the default frontend gate, but remember it runs Biome with `--write --unsafe`; review the diff after running it.
- Use `bun run build` when routing, imports, types, or bundle-time correctness may be affected.
- Use Playwright or equivalent UI verification when critical flows change.
- Use `bash ./scripts/generate-client.sh` from repo root when backend contract
  changes must flow into frontend types.
- For Ant Design dependency changes, prefer `bun install` from the repository
  root so `bun.lock` stays synchronized; if the package manager stalls, record
  that explicitly before handoff.

---

## Delivery Gate Checklist

- [ ] Route files remain thin and delegate to `platform/*/pages` or `features/*/pages`.
- [ ] Route guard, menu visibility, and shared permission helpers agree.
- [ ] API request/response types come from `frontend/src/client/**`.
- [ ] UI changes cover loading, empty, error, permission, and success states when applicable.
- [ ] `shared/*` additions pass the shared admission test in [Component Guidelines](./component-guidelines.md).
- [ ] Any generated files changed by tooling are expected and reviewed.
- [ ] Changed generated client or route-tree files are in the dedicated first
      synchronization commit required by Workflow Phase 3.4.
- [ ] If `bun run lint` was run, its auto-fixes are included intentionally or reverted.
- [ ] Ant Design pages use `app/providers/AntdProvider.tsx`, not local
      per-page theme providers.
- [ ] Ant Design adoption did not silently replace unrelated shadcn/ui pages.

---

## Code Anchors

- Thin routes and page placement: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx), [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx), [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
- Guard and permission flow: [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts), [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts), [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
- Tooling and generated boundaries: [`frontend/package.json`](../../../frontend/package.json), [`frontend/biome.json`](../../../frontend/biome.json), [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
- Ant Design boundary: [`frontend/src/app/providers/AntdProvider.tsx`](../../../frontend/src/app/providers/AntdProvider.tsx), [`frontend/src/platform/docs/pages/RulesPage.tsx`](../../../frontend/src/platform/docs/pages/RulesPage.tsx), [`docs/adr/0001-use-ant-design-for-complex-admin-components.md`](../../../docs/adr/0001-use-ant-design-for-complex-admin-components.md)
