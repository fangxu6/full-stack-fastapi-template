# Improve codebase architecture

## Goal

Identify evidence-backed opportunities to deepen existing modules, then plan
and implement the selected smallest follow-up that improves locality and
testability without broadening into a rewrite.

The first deliverable is an HTML architecture review in the OS temp directory.
The selected follow-up is a narrow frontend permission-access repair described
below. Its implementation was gated on approval of this plan and is now
complete.

## Confirmed Facts

- The backend is intentionally evolving as a modular monolith; simple CRUD
  remains on the lightweight route-to-service-to-crud-to-ORM path.
- HTTP writes use the request-scoped `WriteSessionDep` transaction boundary;
  services and CRUD helpers do not own commit or rollback.
- The external ERP consumer API is deferred and must not be reintroduced by
  this review.
- Recent repository activity includes authentication session authority,
  revocable JWT sessions, cache foundation, inventory workflows, and frontend
  query retry behavior.
- A prior architecture review completed the first frontend permission-access
  deepening; its deferred route/menu metadata work is not repeated here.
- Existing changes must remain untouched; the review phase was analysis-only and
  the selected follow-up stayed within its approved scope.

## Requirements

- Inspect recent commit history to choose review hotspots when the user gives
  no narrower direction.
- Read `CONTEXT.md` and relevant ADRs before forming candidates.
- Trace each candidate through its actual callers, tests, and seams.
- Use the architecture vocabulary: module, interface, depth, deep, shallow,
  seam, adapter, leverage, and locality.
- Apply the deletion test and prefer the smallest deepening that concentrates
  complexity rather than moving it.
- Produce a self-contained HTML report in the OS temp directory with a fresh
  timestamped filename.
- Give each candidate files, problem, solution, benefits, before/after
  visualization, and recommendation strength.
- End the report with one top recommendation.
- Do not propose new interfaces or modify business code before the selected
  follow-up plan is approved and the task enters execution.

## Evidence Anchors

- `frontend/src/app/permissions.ts` owns the shared effective-permission query
  options and route read, but
  `frontend/src/features/inventory/pages/InventoryCorrectionsPage.tsx:92-105`
  calls `IamService.readMyPermissions` directly with the raw query key.
- `backend/app/modules/inventory/service.py:56-975` combines master-unit
  operations, document and ledger mutations, balance reads, exports, and
  suggestions. `importer.py` and `correction_service.py` call into that broad
  implementation for document creation/effects and approved corrections.
- `backend/app/modules/scheduler/service.py:84-536` combines task loading and
  credential validation, job CRUD, run creation, manual operations, cleanup,
  and bootstrap. `tasks.py:35-370` combines alert persistence, scan,
  dispatch leases, Celery execution, and terminal state updates.
- The relevant tests are split across
  `frontend/tests/permission-guards.spec.ts`,
  `backend/tests/api/routes/test_inventory.py`,
  `backend/tests/modules/inventory/test_importer.py`,
  `backend/tests/modules/scheduler/test_scheduler_service.py`, and
  `backend/tests/modules/scheduler/test_scheduler_tasks.py`.

## Acceptance Criteria

- [x] The report path is absolute, outside the repository, and opens or is
      otherwise made available to the user.
- [x] The report contains at least two concrete, code-backed candidates unless
      exploration proves fewer are justified.
- [x] Every candidate names file/module anchors and identifies the relevant
      seam and locality/testability impact.
- [x] Existing ADR decisions are respected or explicitly called out when a
      real friction justifies reopening one.
- [x] The report distinguishes confirmed evidence from recommendation.
- [x] The user selected the permission access candidate and resolved its scope,
      error behavior, and test form through one-question planning.
- [x] `InventoryCorrectionsPage` uses the existing
      `myPermissionsQueryOptions`; no direct permission query remains outside
      the app permission access module.
- [x] The existing permission-guard E2E spec proves `/inventory/corrections`
      shares one permissions request between route guard and page.
- [x] No static quality hook, route/menu metadata consolidation, backend,
      generated-client, dependency, or API contract change is introduced.

## Out of Scope

- Implementing any unselected refactor, new interface, adapter, migration, or
  feature. The selected permission-access caller migration and its focused E2E
  test are the only planned implementation scope.
- Re-litigating the modular-monolith, transaction-boundary, or deferred-ERP
  decisions without concrete friction evidence.
- Creating a repository HTML artifact or changing application behavior.

## Selected Candidate

Candidate 1: restore the frontend permission access module as the only
effective-permission query seam. The current evidence is limited to one
regressing caller in `InventoryCorrectionsPage.tsx`; no broader metadata
consolidation is included.

## Resolved Planning Decisions

- Use the narrow caller migration plus one focused shared-request regression
  test. Do not add a static quality hook or route/menu metadata consolidation.

## Follow-up Scope

- Change `InventoryCorrectionsPage` to use the existing
  `myPermissionsQueryOptions` from `frontend/src/app/permissions.ts`.
- Extend `frontend/tests/permission-guards.spec.ts` with a successful
  `/inventory/corrections` navigation that returns
  `inventory.documents.read` and asserts exactly one permissions request.
- Preserve the page's existing three permission checks and preserve the route
  guard as the owner of permission-read error classification.
- Resolved: the page adds no independent permission-read error state; route
  navigation remains the only classification and redirect surface.

See `deferred-iterations.md` for the explicitly excluded route/menu metadata
consolidation.
