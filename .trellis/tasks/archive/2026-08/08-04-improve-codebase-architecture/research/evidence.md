# Architecture review evidence

## Repository constraints

- `docs/adr/0002-evolve-backend-as-modular-monolith.md`: preserve the modular
  monolith; only bounded capabilities should gain deeper module structure.
- `docs/adr/0006-use-request-scoped-unit-of-work-for-http-writes.md`: HTTP
  writes use `WriteSessionDep`; services and CRUD helpers do not own commit or
  rollback.
- `docs/adr/0001-use-ant-design-for-complex-admin-components.md`: retain the
  existing mixed frontend design system; do not turn an architecture review
  into a component migration.
- `docs/adr/0005-use-celery-redis-for-background-runtime.md` and
  `docs/adr/0009-use-generic-email-outbox-for-non-report-mail.md`: preserve
  PostgreSQL business state and the existing background delivery decisions.

## Hotspots

- Recent changes repeatedly touched inventory Excel workflows, scheduler
  runtime behavior, IAM/audit, generated clients, and frontend route/query
  behavior. The review therefore follows inventory, scheduler, and permission
  paths first.

## Candidate A: permission access module

- `frontend/src/app/router/guards.ts:38-76` calls the generated permission
  interface directly and implements its own error classification.
- `frontend/src/app/navigation/AppSidebar.tsx:18-22` uses a TanStack Query
  for the same data.
- `frontend/src/features/inventory/pages/InventoryDocumentsPage.tsx:136-144`
  and `frontend/src/features/inventory/pages/InventoryBalancesPage.tsx:34-39`
  repeat the query declaration.
- `frontend/src/app/navigation/menu-config.ts:22-64` duplicates route
  permission metadata, while route files repeat the same permission values.
- Current tests cover guard outcomes in `frontend/tests/permission-guards.spec.ts`
  and retry behavior in `frontend/src/app/query-retry.test.ts`, but they do
  not exercise one shared permission access interface across guard, sidebar,
  and page consumers.

## Decision

- The user selected Candidate A for the grilling loop on 2026-08-04.

## Long-term assessment

- Route guards remain the authorization enforcement point; menu filtering is
  only a presentation projection and must not become the security source of
  truth.
- The current route files and `menu-config.ts` duplicate permission metadata.
  With more protected routes, this can drift silently: a page can be guarded
  while its menu entry is visible, or a menu entry can be hidden with a stale
  permission.
- Long term, a single typed route-access metadata source should own the
  permission value and be consumed by both route guards and menu projection.
  The source should not require parsing or hand-editing generated
  `routeTree.gen.ts`.
- This is a separate scope from the immediate permission read/cache/error
  deepening. It becomes worth doing when protected routes continue to grow or
  another route/menu permission drift is observed.

## Planning decision

- The user approved two stages: first permission read/cache/error locality,
  then route/menu permission metadata consolidation.

## Placement assessment

- `frontend/src/app/*` owns application-wide shell, navigation, and router
  guards, so a permission access module belongs under `app` rather than a new
  platform or feature module.
- `frontend/src/shared/permissions/*` should retain pure permission types and
  predicates. The component and directory specs reject promoting API-coupled
  orchestration into `shared/*` merely for import convenience.
- The likely Stage 1 shape is therefore one app-level permission access
  module plus the existing pure shared permission helpers; exact filenames and
  exports remain implementation details until the plan is approved.

## Cache decision

- The user approved sharing one TanStack Query cache and query policy between
  route guards, the sidebar, and feature pages.
- The remaining decision is freshness semantics: preserve the current direct
  guard fetch on each protected navigation, or allow a session-cache result to
  authorize navigation until normal query invalidation/refetch occurs.

## Freshness decision

- The user approved a fresh permission read on every protected navigation.
- The fresh result must populate the shared cache so the sidebar and pages do
  not issue a second permission request for the same state.
- The permission read is a safe GET and can reuse the existing read-query retry
  policy in `frontend/src/app/query-retry.ts`; after retries, the existing
  guard outcomes remain 401 -> login, 403 -> configuration error, and other
  failures -> retryable forbidden state.

## Migration coverage decision

- The current scope still needs to decide whether every existing permission
  consumer moves to the shared access module or only the route guard and
  sidebar.

## Consumer coverage decision

- The user approved migrating every current permission consumer: route guards,
  sidebar, inventory master/document/balance pages, and scheduler pages.
- The remaining shape decision is how one module serves both TanStack Query
  components and the non-React route guard without creating a second fetch
  path.

## Module shape decision

- The user accepted a shared query-options seam plus a non-React read entry for
  the route guard.
- The repository has no existing permission query-options helper. Existing
  query freshness examples use a bounded `staleTime` (`RulesPage`) or an
  explicit `refetchOnMount` policy (`SchedulerJobsPage`).
- To preserve one request per navigation, the guard should force a fresh
  `fetchQuery` while component observers use the shared options with a short
  bounded stale window; the exact window remains open.

## Freshness window decision

- The user approved a 30-second component-side `staleTime`.
- Route guards still force a fresh read on protected navigation. Backend
  authorization remains authoritative; the window only bounds UI/menu state
  staleness and prevents a second request after navigation.

## Stage 1 implementation evidence

- `frontend/src/app/permissions.ts` now owns the shared permission query
  options, 30-second component freshness, route-error classification, and
  the non-React fresh navigation read.
- `frontend/src/app/query-client.ts` owns the singleton `QueryClient` used by
  both the router guard and `QueryClientProvider`.
- The sidebar, inventory master/document/balance pages, and scheduler page all
  use the same query options. The generated client, route tree, pure shared
  permission helpers, and route/menu metadata were not changed.
- `frontend/src/app/permissions.test.ts` checks the query contract, existing
  guard unit tests retain the error outcomes, and
  `frontend/tests/permission-guards.spec.ts` verifies one permission request
  is shared between protected navigation and the page.
- Validation passed: focused Bun tests (8 passed), permission Playwright
  tests (8 passed), `bun run build`, `bun run lint`, and `git diff --check`.

## Candidate B: inventory document/ledger module

- `backend/app/modules/inventory/service.py:246-375` creates document lines
  and ledger entries, validates document types, and rejects negative balances.
- The same file also owns master-unit operations at `:51-243`, read-side
  balance/ledger aggregation at `:602-837`, and suggestion queries at `:878`.
- `backend/app/modules/inventory/importer.py:74-754` combines workbook parsing,
  legacy conversion, audit actor binding, database writes, and transaction
  rollback behavior.
- The route surface is concentrated in
  `backend/app/modules/inventory/router.py:101-470`; the current test surface
  is primarily `backend/tests/api/routes/test_inventory.py` plus core Excel
  tests, leaving a less local module interface for document/ledger invariants.

## Candidate C: scheduler definition/run module

- `backend/app/modules/scheduler/service.py:85-508` combines cron utilities,
  class-path task resolution, credential-like schema validation, job CRUD,
  manual run policy, run persistence, and cleanup.
- `backend/app/modules/scheduler/tasks.py:35-368` owns alert outbox creation,
  queue dispatch, due-job scanning, execution, retry handling, and cleanup,
  with several explicit transaction phases.
- Existing scheduler specs and tests are strong, so this is a lower-confidence
  deepening candidate than the permission and inventory paths.
