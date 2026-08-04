# Architecture review design

## Scope

The review selected a frontend permission access deepening. Stage 1 is a
frontend-only implementation; Stage 2 route/menu permission metadata
consolidation is explicitly deferred in `deferred-iterations.md`.

## Evidence path

1. Read `CONTEXT.md` and the ADRs that constrain module shape, transactions,
   frontend composition, background work, and persistence.
2. Use recent git history to find areas with repeated change or cross-module
   movement.
3. Trace selected paths through source, tests, generated contracts, and
   configuration until the current interface/seam is understood.
4. Apply the deletion test: a candidate is useful only when removing or
   consolidating shallow modules would concentrate complexity rather than move
   it elsewhere.

## Candidate shape

Each candidate will describe:

- the affected module and files;
- the current interface, implementation, and seam friction;
- the smallest deepening that improves locality;
- why the change provides leverage across callers or tests;
- compatibility and ADR implications;
- a before/after diagram.

The report will use the existing architecture vocabulary and will not propose
interfaces before the user selects a candidate for grilling.

## Output

Write one self-contained report to the platform temp directory using the
provided HTML scaffold. Use CDN Tailwind and Mermaid only in that report; no
repository asset or package change is needed.

## Decision gate

The report ends with a top recommendation and the question: which candidate
should be explored? The selected candidate becomes a separate planning
decision inside this task before any implementation authorization.

## Stage 1 Technical Design

### Ownership

- Keep pure `PermissionCode`, `hasPermission`, and safe-path helpers in
  `frontend/src/shared/permissions/*`.
- Add an app-level permission access module because `app/*` owns global
  navigation and route guards. It owns the generated-client read, shared query
  options, 30-second component freshness, and final error classification.
- Move `QueryClient` construction out of `main.tsx` into an app-level module.
  `main.tsx` imports the same instance for `QueryClientProvider`; route guards
  import it for the non-React read entry.

### Data Flow

1. `requirePermission` calls the access module's non-React read entry.
2. The entry uses `queryClient.fetchQuery` with the shared permission query
   options and a fresh-navigation override, writing the result to the shared
   cache.
3. The route guard applies the existing redirect outcomes to the result or
   final error.
4. Sidebar and feature pages call `useQuery` with the same options. Their
   30-second stale window reuses the guard result and prevents a second mount
   request after navigation.
5. The existing safe-GET retry policy remains the query default. No backend,
   OpenAPI, or dependency change is needed.

### Contracts

- Query key remains `["iam", "permissions"]`.
- Query function remains generated `IamService.readMyPermissions`.
- 401 -> login; 403 -> configuration forbidden; other final errors -> retry
  forbidden; missing permission -> ordinary forbidden.
- Backend authorization remains authoritative. The 30-second window affects
  UI/menu state only.

### Compatibility and Rollback

- No API or generated-client contract changes are expected.
- Existing route and menu permission literals remain unchanged in Stage 1.
- Rollback is file-scoped: restore the current local QueryClient construction,
  direct guard read, and repeated page query declarations. Stage 2 metadata is
  not entangled with this rollback.
