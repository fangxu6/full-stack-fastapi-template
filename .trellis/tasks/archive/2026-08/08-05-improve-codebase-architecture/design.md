# Architecture review design

## Scope

The review phase is analysis-only and produces a temporary HTML report and a
ranked set of candidates. The selected follow-up has a separate implementation
plan below; it does not add a new interface or change production code until the
plan is approved and execution starts.

The prior 08-04 architecture task is historical context: its permission
access Stage 1 was completed, and route/menu metadata consolidation remains a
separate deferred iteration. This review checks current reality after the
recent inventory-correction addition instead of repeating that prior scope.
The explicitly deferred route/menu metadata work is tracked in
`deferred-iterations.md`.

## Evidence path

1. Read `CONTEXT.md`, the modular-monolith and transaction ADRs, the LLM-Wiki
   index, and the backend/frontend architecture sources.
2. Use recent commit history and changed-file frequency to select hotspots.
3. Trace current callers, implementations, and tests for each hotspot.
4. Apply the deletion test: keep a candidate only when deleting or
   consolidating shallow modules would concentrate complexity and improve
   locality rather than move it.

## Candidates

- Restore the frontend permission access module as the only effective-
  permission query seam. This is a small, strong candidate because a new
  feature regressed to a direct generated-client query after the module was
  centralized.
- Deepen the inventory document/ledger mutation module. Keep the document and
  ledger invariant local while separating master-unit and read/export concerns
  from the broad current implementation.
- Deepen the scheduler runtime around the durable run lifecycle. Separate
  definition/configuration concerns from scan, dispatch, execution, and alert
  concerns while preserving PostgreSQL as source of truth and Celery as the
  numeric-ID transport.

## Decision gate

The report ends by asking which candidate the user wants to explore. Only the
selected candidate may proceed to a grilling pass and a new implementation
plan. No implementation starts from this review alone.

## Selected Candidate Design

### Scope

- Import `myPermissionsQueryOptions` in
  `frontend/src/features/inventory/pages/InventoryCorrectionsPage.tsx` and
  pass it directly to `useQuery`.
- Keep the existing `canRequest`, `canReview`, and `canRecover` predicates.
- Extend `frontend/tests/permission-guards.spec.ts` with the corrections route
  and assert that the route guard and page share one permissions request.
- Leave `frontend/src/app/permissions.ts`, route/menu metadata, and the shared
  permission predicate implementation unchanged.

### Contract

- The query key remains `['iam', 'permissions']`.
- The query function remains `IamService.readMyPermissions`, owned by the app
  permission access module.
- Route navigation still performs the fresh read with `staleTime: 0`.
- The corrections page observes the same query with the 30-second UI freshness
  window.
- The route guard remains responsible for 401, 403, retryable, and missing
  permission outcomes; the page does not add a second error policy.

### Compatibility

- No backend, generated-client, route-tree, dependency, or API contract change
  is expected.
- The page's existing three correction permission checks remain behaviorally
  unchanged.
