# Architecture review and Stage 1 execution plan

## Preconditions

1. Review this plan and approve implementation.
2. Run `python ./.trellis/scripts/task.py start 08-04-improve-codebase-architecture`.
3. Load `trellis-before-dev` and the frontend spec index before editing.

## Implementation

1. Move the existing `QueryClient` construction and error handlers from
   `frontend/src/main.tsx` to an app-level module consumed by both
   `main.tsx` and route guards.
2. Add the app-level permission query/access module with the shared key and
   generated read function, 30-second component `staleTime`, fresh guard read,
   and existing error classification.
3. Migrate every current permission consumer: route guards, sidebar, inventory
   master/document/balance pages, and scheduler pages.
4. Remove local permission query declarations. Preserve unrelated scheduler
   query policies, including the cron-preview `refetchOnMount: "always"`
   override.
5. Leave `shared/permissions/*`, route permission literals, menu metadata, the
   generated client, and `routeTree.gen.ts` unchanged except for imports that
   are strictly required by Stage 1.

## Validation

- Add a focused Bun test for query sharing/freshness and error classification.
- Preserve and run `frontend/tests/permission-guards.spec.ts`.
- Add or update one permission navigation check proving the guard result is
  reused by the page without a second permission request.
- From `frontend/`: `bun test <focused permission test paths>`.
- From `frontend/`: `bunx playwright test tests/permission-guards.spec.ts`.
- From `frontend/`: `bun run build`.
- From `frontend/`: `bun run lint`; review its write diff.
- From the repository root: `git diff --check`.

## Review Gates

- No backend, OpenAPI, generated-client, dependency, or Stage 2 metadata diff.
- Existing 401, 403, retryable, ordinary-forbidden, and successful permission
  outcomes remain covered.
- Query calls are centralized: no direct `IamService.readMyPermissions` or
  repeated `['iam', 'permissions']` declarations remain outside the access
  module.
- Final full-scope frontend quality check passes before commit planning.

## Rollback

Restore only the app query-client/access changes and consumer imports if the
shared cache behavior is incorrect. Do not revert unrelated working-tree
changes or implement the deferred route/menu metadata item as a workaround.
