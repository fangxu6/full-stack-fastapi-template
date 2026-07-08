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
- Respect Biome exclusions and generated/vendor-style boundaries from
  [`frontend/biome.json`](../../../frontend/biome.json).

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

---

## Cross-Layer Review Rules

- If backend schema changed, regenerate the frontend client.
- If route or permission behavior changed, verify route guards, navigation visibility, and redirect behavior together.
- If generated client output changed, verify consumers import generated services/types instead of recreating local API contracts.
- If route tree generation changed, verify route files remain thin and `frontend/src/routeTree.gen.ts` is generated output, not hand-edited business code.
- If a page changed, check for regressions in:
  - empty state
  - error state
  - permission state
  - loading state
- If a UI flow changed, check success, failed mutation, pending/loading, and no-data states instead of only the happy path.

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

---

## Delivery Gate Checklist

- [ ] Route files remain thin and delegate to `platform/*/pages` or `features/*/pages`.
- [ ] Route guard, menu visibility, and shared permission helpers agree.
- [ ] API request/response types come from `frontend/src/client/**`.
- [ ] UI changes cover loading, empty, error, permission, and success states when applicable.
- [ ] `shared/*` additions pass the shared admission test in [Component Guidelines](./component-guidelines.md).
- [ ] Any generated files changed by tooling are expected and reviewed.
- [ ] If `bun run lint` was run, its auto-fixes are included intentionally or reverted.

---

## Code Anchors

- Thin routes and page placement: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx), [`frontend/src/routes/_layout/items.tsx`](../../../frontend/src/routes/_layout/items.tsx), [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
- Guard and permission flow: [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts), [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts), [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
- Tooling and generated boundaries: [`frontend/package.json`](../../../frontend/package.json), [`frontend/biome.json`](../../../frontend/biome.json), [`scripts/generate-client.sh`](../../../scripts/generate-client.sh)
