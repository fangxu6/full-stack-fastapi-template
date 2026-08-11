# Refactor Frontend Legacy Directories

## Goal

Align the frontend source tree with the established `app`, `platform`,
`features`, `shared`, and thin-`routes` ownership model. Relocate reusable and
domain-owned code from the legacy roots and remove those roots without changing
user-visible behavior.

## Background

The frontend currently has 32 tracked source files in the legacy roots:
27 under `frontend/src/components/` (24 shadcn/ui primitives, a theme
provider, and two pending-state components), 4 hooks, and 1 `lib/utils.ts`.
Sixty-five frontend files import these paths. The shadcn aliases in
`frontend/components.json`, Biome, the project frontend quality hook and tests,
active Trellis guidance, `ARCHITECTURE.md`, `CODING_STANDARDS.md`, and
`README.md` all encode the old locations.

The current shadcn/ui implementations remain required by working screens.
`useAuth` owns the authentication session contract and has 14 callers, so it
belongs to `platform/auth`; the other legacy hooks are generic browser/UI
behavior. Pending components are consumed only by their existing shared
feedback entrypoints. The root `frontend/src/utils.ts` contains generic
`handleError` and `getInitials` helpers with 13 consumers and is included in
this migration.

## Requirements

1. Retain the existing shadcn/ui implementations as vendor-style source under
   `frontend/src/shared/components/ui/`; do not replace them with Ant Design.
2. Move the theme provider and generic hooks into `shared/*`, move `useAuth`
   into the platform-auth boundary, merge each Pending implementation into its
   existing `shared/components/feedback/*TableSkeleton` entrypoint, and move
   both utility files into `shared/utils`.
3. Update all production imports, internal primitive imports, shadcn aliases,
   Biome exclusions, quality-hook policy/tests, and repository guidance to the
   final paths. Do not retain compatibility aliases or wrapper re-exports under
   the old roots.
4. Preserve current UI behavior, route contracts, auth/session behavior,
   generated-client and route-tree boundaries, and public API contracts.

## Acceptance Criteria

- [x] `frontend/src/components`, `frontend/src/hooks`, and
      `frontend/src/lib` no longer exist, and `frontend/src/utils.ts` is gone.
- [x] Every moved file has one final owner under `shared/*` or `platform/*`;
      no active source import, generator alias, or quality rule references the
      retired paths.
- [x] The shadcn generator resolves `shared/components/ui` and `shared/utils`,
      and vendor-style edit protection follows the relocated primitives.
- [x] Frontend build, read-only Biome check, focused quality-hook tests, and
      migration-related browser regressions pass. The 13 full-suite baseline
      failures are owned by
      [08-11-reconcile-frontend-e2e-baseline](../08-11-reconcile-frontend-e2e-baseline/prd.md).
- [x] Targeted stale-path searches find no active reference to the retired
      directories or aliases, excluding historical task archives/changelogs.

## Out Of Scope

- Replacing shadcn/ui with Ant Design or redesigning visual behavior.
- Backend APIs, generated OpenAPI client output, route-tree generation,
  dependencies, authentication behavior, or feature workflows.
- Moving code that already conforms to the target ownership model merely for
  stylistic uniformity.
