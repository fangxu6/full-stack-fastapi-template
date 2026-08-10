# Refresh Frontend And Guide Spec Contracts

## Goal

Correct the remaining active-specification drift in frontend access guidance,
thinking guides, and feature boundaries without changing product behavior.
The user value is safer future frontend work: page access, navigation, action
capabilities, and reuse choices must follow the current implementation rather
than retired template-era examples.

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
- **F-006 (P3):** `.trellis/spec/index.md:13-20` still describes the
  2026-07-08 merge as the active-current baseline. The database and async
  guides are now 1,473 and 806 lines, respectively, but their scenario
  contracts and `backend/index.md` trigger routing remain usable. Length alone
  does not establish a safe split; a mechanical reorganization would add link
  and wording drift without correcting an observable contract defect.

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
6. Remove the dated active-current baseline from the root catalog and make the
   corrected frontend contracts the canonical owners. Thinking guides may link
   to those owners, but must not restate their implementation signatures.
   Preserve the existing backend trigger indexes and durable scenarios; defer
   splitting `database-guidelines.md` or `async-task-guidelines.md` until a
   concrete navigation, validation, or duplicate-contract failure justifies it.
7. Do not modify async guidance for F-006. The completed scheduler-lifecycle
   ownership contract remains a protected out-of-scope dependency.

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
- [ ] The route-permission contract, component-placement guide, and state guide
      are the canonical owners of their respective frontend rules; thinking
      guides link to them without duplicating signatures.
- [ ] The root catalog no longer calls a dated merge event the active-current
      baseline, while `backend/index.md` continues to route database and async
      work to their durable scenario contracts.
- [ ] No active requirement asks for a mechanical split of the long backend
      guides; such a split is explicitly deferred until a concrete usability or
      duplication failure is evidenced.
- [ ] `python .trellis/scripts/spec_wiki.py lint`, path-scoped stale-term
      searches, `python .trellis/scripts/task.py validate <task-dir>`, and
      `git diff --check` pass.

## Scope

In scope:

- Active `.trellis/spec/frontend/**`, `.trellis/spec/guides/**`, and shared
  indexes/links needed for F-003 through F-006.
- The root catalog wording and canonical links needed for F-003 through F-006.
- This task's planning artifacts and source-evidence snapshot.

Out of scope:

- Changes under `backend/app/**`, `frontend/src/**`, generated clients,
  database schema, dependencies, migrations, or runtime configuration.
- Moving the existing scheduler-to-inventory pagination helper during this
  documentation task.
- Splitting, moving, or mass-reformatting `database-guidelines.md` or
  `async-task-guidelines.md` solely because of line count.
- A global state-management redesign, generic Clean Architecture rewrite, or
  historical-record rewrite.
