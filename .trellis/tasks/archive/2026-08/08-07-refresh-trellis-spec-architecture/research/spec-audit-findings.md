# 2026-08-07 Trellis Spec Audit Evidence

## Audit Scope And Baseline

- Scope: read-only evaluation of all active `.trellis/spec` guidance against
  current source, focused tests, routing, and recent refactors.
- Structural result: `python .trellis/scripts/spec_wiki.py lint` reported zero
  errors and zero warnings. This verifies indexes and links, not semantic
  freshness.
- Working tree at audit start: clean.
- Recent source changes after the latest relevant spec updates included
  `8b99ff9`, `89228e4`, `1d7f4d2`, `4542874`, and `83b4502`.

## F-001 P1: Backend Architecture Is Presented As A Future Transition

### Stale guidance

- `.trellis/spec/backend/index.md:9-15,61-79` calls the repository a
  `platform-batch-0 transition`, says most business behavior is service-first,
  and calls `modules/*` future-facing.
- `.trellis/spec/backend/directory-structure.md:9,45-47,69-70` repeats that
  modules are future-facing and should remain secondary until they are richer.
- `.trellis/spec/backend/quality-guidelines.md:249-261` says modules are not
  already mature.

### Current evidence

- `backend/app/api/main.py:5-23` registers inventory, inventory corrections,
  IAM, and scheduler module routers in the production API aggregation path.
- `backend/app/modules/` contains active `audit`, `auth`, `file`, `iam`,
  `inventory`, `items`, `scheduler`, and `system` boundaries.
- Inventory owns documents, ledger, correction attempts, workbook adapters,
  and scheduled tasks. Scheduler owns orchestration, execution outcomes,
  lifecycle transitions, and alert ownership.

### Required resolution

State the hybrid architecture as current reality. Keep simple CRUD lightweight;
select a module boundary only for real bounded-domain complexity. Do not call
operational modules future-facing.

## F-002 P1: Scheduler Lifecycle Guidance Names Removed Ownership And API

### Stale guidance

- `.trellis/spec/backend/async-task-guidelines.md:208-225` assigns scheduler
  scanning and execution to `tasks.py` and calls
  `run_lifecycle.finish_run(...)`.

### Current evidence

- `backend/app/modules/scheduler/tasks.py` now registers Celery task names.
- `backend/app/modules/scheduler/orchestration.py:42-230` owns dispatch,
  due-job scanning, execution phases, and cleanup.
- `backend/app/modules/scheduler/execution.py:20-69` returns a
  `SchedulerRunOutcome` from frozen task execution.
- `backend/app/modules/scheduler/run_lifecycle.py:176-194` owns the terminal
  `finish_outcome(...)` persistence transition.

### Required resolution

Replace the obsolete example and document the five-part ownership split:
registration, orchestration, execution outcome, lifecycle persistence, and
job-alert/outbox handling.

## F-003 P2: Frontend Route Permission Contract Uses Obsolete Interfaces

### Stale guidance

- `.trellis/spec/frontend/route-permission-navigation-contract.md:34-41`
  names `requireSuperuser()` and `canAccessAdmin(user)` as the interfaces.
- Lines `70-86` require the same obsolete superuser model in its cases.
- Lines `45-50` omit current route search validation from allowed thin-route
  responsibilities.
- `.trellis/spec/frontend/state-management.md:87` still describes permission
  behavior as current-user-derived rather than permission-query-derived.

### Current evidence

- `frontend/src/app/router/guards.ts:24-66` exposes
  `requirePermission(permission)` and reads fresh permission data.
- `frontend/src/shared/permissions/index.ts:1-23` owns `PermissionCode` and
  `hasPermission`.
- `frontend/src/app/navigation/menu-config.ts:73-78` filters menu entries from
  permission codes.
- `frontend/src/routes/_layout/inventory/corrections.tsx:7-14` uses Zod
  `validateSearch` while staying a thin route.
- `frontend/src/features/inventory/correction-workspace.ts:37-54` derives
  request/review/recovery action capabilities on a route already gated by the
  document-read permission.

### Required resolution

Use permission-code contracts, distinguish page access from action capabilities,
and allow route-local search/input declaration. Backend endpoints remain the
authorization authority.

## F-004 P2: Cross-Layer And Reuse Guides Treat Legacy Services As Universal

### Stale guidance

- `.trellis/spec/guides/cross-layer-thinking-guide.md:29-56` describes the
  canonical data flow and boundary table as route/service/CRUD only.
- `.trellis/spec/guides/code-reuse-thinking-guide.md:47-56,113-135` makes the
  same service-first placement statement.
- `.trellis/spec/guides/code-reuse-thinking-guide.md:74-81` uses the retired
  `is_superuser` example.
- `.trellis/spec/guides/index.md:131-137` says to prefer `rg`, conflicting
  with the repository CodeGraph-first instruction for code understanding.

### Required resolution

Present simple CRUD and bounded modules as alternate source-backed paths;
replace superuser examples with permission codes; route code understanding and
impact analysis through CodeGraph, keeping `rg` for narrow text/spec checks.

## F-005 P2: Feature-To-Feature Dependency Policy Is Missing

### Current evidence

- `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:43-47` imports
  generic pagination values from `frontend/src/features/inventory/pagination.ts`.
- `.trellis/spec/frontend/component-guidelines.md:35-41` correctly defines
  admission to `shared/*`, but no rule prohibits one feature becoming another
  feature's utility provider.

### Required resolution

Add a no-new-cross-feature-import rule: relocate genuinely shared,
domain-neutral behavior to `shared/*` once admitted, or keep trivial code
local. Record the current pagination import as a follow-up source cleanup;
this documentation task does not move it.

## F-006 P3: Large And Duplicated Specs Raise Future Drift Risk

### Evidence

- `backend/database-guidelines.md` is 1,399 lines.
- `backend/async-task-guidelines.md` is 796 lines.
- Static architecture, generated-client, and route/permission requirements are
  restated in indexes, quality guides, and thinking guides.
- `.trellis/spec/index.md:13-20` calls itself current after the 2026-07-08
  merge despite subsequent architecture refactors.

### Required resolution

Use compact trigger indexes and canonical owners. Move existing scenario
sections rather than duplicating them, keep the append-only log as history,
and remove historical event wording from active-current claims.

## Verified Rules To Preserve

- Request Unit of Work, rollback, and deferred cache invalidation.
- Explicit audit actor and System Actor handling.
- Structured logging, request correlation, and approved HTTP/Celery exception
  boundaries.
- At-least-once Celery design, durable scheduler state, idempotency, and outbox
  delivery.
- Generated frontend client discipline, controlled server pagination, and thin
  route/page placement.

## Audit Limits

- No product source, tests, runtime configuration, database, or generated
  artifacts were changed.
- No full backend or frontend quality gate was run because the audit was
  documentation-only.
