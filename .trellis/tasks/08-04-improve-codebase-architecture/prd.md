# Improve codebase architecture review

## Goal

Identify the highest-leverage opportunities to deepen the current backend and
frontend modules, improving locality, testability, and AI navigability without
starting a broad rewrite.

## Background

- The requested scope is the repository's `backend/` and `frontend/` modules.
- The repository already records a modular-monolith direction in ADR-0002;
  simple CRUD should stay lightweight and only genuinely bounded capabilities
  should gain deeper module structure.
- Existing decisions are constraints, not automatic refactoring targets:
  Ant Design for complex admin interfaces (ADR-0001), request-scoped HTTP
  transactions (ADR-0006), Celery/Redis for background runtime (ADR-0005),
  and the generic email outbox (ADR-0009).

## Requirements

- Inspect `CONTEXT.md`, relevant ADRs, recent commit history, and the actual
  backend/frontend source and tests before proposing candidates.
- Use the architecture vocabulary `module`, `interface`, `implementation`,
  `depth`, `deep`, `shallow`, `seam`, `adapter`, `leverage`, and `locality`.
- Produce a small set of evidence-backed deepening candidates. Each candidate
  must identify files, the current friction, the proposed change, expected
  locality/leverage/test gains, and any ADR tension.
- Present each candidate with a before/after visualisation in a self-contained
  HTML report written to the OS temp directory, not the repository.
- Keep this task in evaluation/planning mode. Do not implement a candidate,
  add a dependency, or modify production code until the user selects and
  approves a follow-up scope.

## Acceptance Criteria

- [x] `CONTEXT.md`, relevant ADRs, recent history, and both module trees have
      been inspected; findings are anchored to current files.
- [x] The report contains at least two non-speculative candidates, with files,
      problem, solution, benefits, recommendation strength, and before/after
      diagrams.
- [x] The report names one top recommendation and records why it has the best
      leverage/locality payoff for the smallest credible scope.
- [x] The report is written outside the repository and opened or otherwise
      exposed at an absolute path.
- [x] The user is asked which candidate to explore next; no implementation is
      started before that choice and a reviewed plan.

## Out of Scope

- Full Clean Architecture or microservice migration.
- Broad frontend design-system migration.
- New API, database schema, dependency, deployment, or observability work.
- Re-litigating an ADR without concrete friction found in current code.

## Selected Candidate

Candidate A: deepen the frontend permission access module. The first planning
decision is whether to keep this as a narrow data-access deepening or include
route/menu permission metadata deduplication in the same scope.

Long-term assessment: merge the duplicated permission metadata into one typed
route-access source, while keeping route guards as the authorization
enforcement point and menu filtering as presentation. Do not derive it by
editing or parsing generated `frontend/src/routeTree.gen.ts`. Whether to add
that metadata work to this task remains open; the immediate recommendation is
to keep it separate unless route growth or repeated drift justifies the larger
scope.

## Confirmed Planning Decision

- The user approved two stages: Stage 1 deepens permission data access; Stage 2
  later consolidates route/menu permission metadata.

The approved deferred work is tracked in `deferred-iterations.md`; it is not
part of Stage 1 acceptance.

Current placement recommendation: keep pure predicates/types in
`frontend/src/shared/permissions/*` and place API/query/error orchestration in
an app-level module because `app/*` owns global navigation and route guards.

The user also approved sharing one TanStack Query cache and query policy across
route guards, the sidebar, and feature pages. Permission freshness semantics
are now fixed: each protected navigation performs a fresh read, writes the
result to shared cache, and preserves the current final error outcomes. The
read may reuse the existing safe-GET retry policy. Migration coverage across
all current permission consumers is fixed: route guards, sidebar, inventory
master/document/balance pages, and scheduler pages all move to the same access
module.

The module shape is also fixed: components and the non-React route guard share
one query-options seam; the guard uses a fresh `fetchQuery`, while component
observers use a bounded UI freshness window to avoid a second request after
navigation. The approved window is 30 seconds; backend authorization remains
authoritative while UI/menu state may be stale within that window.

## Stage 1 Acceptance Criteria

- [x] One app-level permission access module owns the permission query options,
      error classification, and non-React route-read entry.
- [x] `QueryClient` is app-level and shared by the router and
      `QueryClientProvider`; no second client or direct guard fetch remains.
- [x] Every current permission consumer uses the shared query options: route
      guards, sidebar, inventory master/document/balance pages, and scheduler.
- [x] Protected navigation performs a fresh permission read; component
      observers use a 30-second `staleTime` and do not duplicate that request
      on mount.
- [x] Existing outcomes remain unchanged: 401 redirects to login, 403 routes
      to the configuration error, other final failures route to retryable
      forbidden, and missing permission routes to ordinary forbidden.
- [x] Focused frontend unit/E2E checks cover query sharing/freshness and all
      existing permission-guard outcomes; frontend build and lint pass.
- [x] `shared/permissions/*` remains pure and Stage 2 route/menu metadata work
      remains deferred.

## Confirmed Evidence

- `frontend/src/app/router/guards.ts:38-76` fetches effective permissions
  directly, while `frontend/src/app/navigation/AppSidebar.tsx:18-22` and
  multiple feature pages independently declare the same
  `['iam', 'permissions']` query. Route permission values are also repeated
  in route files and `frontend/src/app/navigation/menu-config.ts:22-64`.
- `backend/app/modules/inventory/service.py:51-837` combines master-unit CRUD,
  document commands, ledger creation/deletion, balance aggregation, and
  suggestions behind one implementation. The document/ledger invariant is
  exercised mainly through `backend/tests/api/routes/test_inventory.py`, while
  the workbook orchestration in `backend/app/modules/inventory/importer.py:74-754`
  crosses Excel parsing, audit binding, persistence, and legacy compatibility.
- `backend/app/modules/scheduler/service.py:85-508` combines cron preview,
  dynamic task definition validation, job CRUD, run creation, capability
  checks, cleanup, and bootstrap. `backend/app/modules/scheduler/tasks.py:35-368`
  combines alert outbox creation, queue dispatch, scan, execution, retry, and
  cleanup transaction phases.
