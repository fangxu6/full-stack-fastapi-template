# Refresh Frontend And Guide Spec Contracts

## Goal

Resolve the remaining audit findings in frontend access guidance, cross-layer
and reuse guidance, feature boundaries, and specification governance without
changing product behavior.

## Confirmed Findings

- **F-003 (P2):**
  `.trellis/spec/frontend/route-permission-navigation-contract.md:34-41,70-86`
  still names `requireSuperuser()` and `canAccessAdmin(user)`. It omits route
  search validation at lines 45-50, and
  `.trellis/spec/frontend/state-management.md:87` describes permissions as
  current-user-derived.
- Current frontend evidence is permission-code based:
  `frontend/src/app/router/guards.ts:24-66` exposes
  `requirePermission(permission)`; `frontend/src/shared/permissions/index.ts:1-23`
  owns `PermissionCode` and `hasPermission`; and
  `frontend/src/app/navigation/menu-config.ts:73-78` filters menus from those
  codes. `frontend/src/routes/_layout/inventory/corrections.tsx:7-14` proves
  `validateSearch` can remain in a thin route, while
  `frontend/src/features/inventory/correction-workspace.ts:37-54` separates
  page access from request/review/recovery action capabilities.
- **F-004 (P2):**
  `.trellis/spec/guides/cross-layer-thinking-guide.md:29-56` and
  `.trellis/spec/guides/code-reuse-thinking-guide.md:47-56,113-135` present
  route/service/CRUD as universal. The reuse guide's `is_superuser` example
  is retired at lines 74-81. `.trellis/spec/guides/index.md:131-137` says to
  prefer `rg`, conflicting with the repository's CodeGraph-first instruction
  for code understanding.
- **F-005 (P2):** The specification has no cross-feature dependency rule.
  `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:43-47` imports
  generic pagination values from
  `frontend/src/features/inventory/pagination.ts`, despite the shared-admission
  rule in `.trellis/spec/frontend/component-guidelines.md:35-41`.
- **F-006 (P3):** `backend/database-guidelines.md` is 1,399 lines and
  `backend/async-task-guidelines.md` is 796 lines. Static contracts are
  duplicated across indexes, quality guides, and thinking guides, and
  `.trellis/spec/index.md:13-20` calls its 2026-07-08 state current despite
  later architecture refactors.

## Requirements

1. Revalidate every source-backed claim before editing. Use CodeGraph first for
   code understanding and impact analysis; use `rg` only for narrow text,
   specification, and link checks.
2. Replace obsolete frontend superuser interfaces with the permission-code
   contract. Distinguish permission-query-driven page/menu access from
   action-level client capabilities, and retain backend endpoint authorization
   as the authority.
3. Allow thin routes to declare transport concerns such as `validateSearch`
   while keeping page implementation and feature orchestration outside
   `routes/*`.
4. Present simple CRUD and bounded-domain modules as supported alternate paths
   in cross-layer and reuse guides. Replace retired superuser examples.
5. Add a no-new-cross-feature-import rule: move genuinely shared,
   domain-neutral behavior to `shared/*` only after the existing admission
   test passes; keep trivial code local. Record the current scheduler-to-
   inventory pagination import as a source-cleanup follow-up, not as an
   authorized product change.
6. Establish canonical owners and compact trigger routing for duplicated or
   oversized active guidance. Move existing scenario content rather than
   creating generic template policy, retain durable invariants, and remove
   stale active-current event wording while preserving historical records.
7. Before modifying async guidance for F-006, incorporate the completed
   scheduler-lifecycle child task's corrected ownership contract. This is an
   ordering constraint to prevent reintroducing F-002, not a permission to
   alter product source.

## Acceptance Criteria

- [ ] Route and navigation guidance uses `PermissionCode`, `hasPermission`,
      and `requirePermission(permission)`; it correctly separates page/menu
      access from action capabilities and backend authorization.
- [ ] Thin-route guidance allows `validateSearch` and still excludes page
      implementation and feature orchestration from `routes/*`.
- [ ] Cross-layer and reuse guides support both simple CRUD and complex module
      workflows, contain no retired superuser example, and prescribe
      CodeGraph-first source exploration.
- [ ] Frontend placement guidance prohibits new feature-to-feature utility
      imports, gives a `shared/*` admission path for genuinely shared behavior,
      permits trivial local duplication, and records the existing pagination
      import as future product-source cleanup.
- [ ] Each repeated architecture, permission/route, and feature-boundary
      contract has one canonical active owner; indexes and related guides link
      to it rather than restating implementation signatures.
- [ ] Oversized database and async guidance has trigger-based entry points that
      preserve durable invariants and the scheduler ownership correction.
- [ ] Active indexes do not call a superseded dated merge state current.
- [ ] `python .trellis/scripts/spec_wiki.py lint`, path-scoped stale-term
      searches, `python .trellis/scripts/task.py validate <task-dir>`, and
      `git diff --check` pass.

## Scope

In scope:

- Active `.trellis/spec/frontend/**`, `.trellis/spec/guides/**`, and shared
  indexes/links needed for F-003 through F-006.
- Trigger routing or focused splits in active database and async guidance when
  they reduce duplicated first-read context without losing an invariant.
- This task's planning artifacts and the parent integration record.

Out of scope:

- Changes under `backend/app/**`, `frontend/src/**`, generated clients,
  database schema, dependencies, migrations, or runtime configuration.
- Moving the existing scheduler-to-inventory pagination helper during this
  documentation task.
- A global state-management redesign, generic Clean Architecture rewrite, or
  historical-record rewrite.

## Planning Constraint

This is a complex documentation task because it can reorganize several
cross-linked contracts. Add a design and implementation plan, including the
F-002 ordering constraint, before `task.py start`.

## Open Questions

None. The audit evidence resolves the required scope and source authority.
