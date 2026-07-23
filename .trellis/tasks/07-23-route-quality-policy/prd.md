# Enforce thin route entries with AST validation

## Goal

Replace heuristic route component checks with TypeScript AST validation, preserve root shell exception, and migrate the dashboard route to a page module.

## Requirements

1. Use TypeScript AST analysis for changed, existing `frontend/src/routes/**`
   entries instead of naming-based text heuristics.
2. Ordinary routes may configure `Route` and reference imported components, but
   must not declare local components or use inline component callbacks.
3. Keep `frontend/src/routes/__root.tsx` as the sole Router-shell exception for
   its existing inline framework callbacks.
4. Skip deleted paths in the frontend quality hook while preserving all checks
   for existing generated, vendor, shared, and component paths.
5. Move the dashboard implementation out of `routes/_layout/index.tsx` to a
   platform page module without changing the `/` route.
6. Preserve existing uncommitted RBAC work and do not regenerate or edit the
   SDK or route tree.

## Acceptance Criteria

- [ ] Thin route entries with imported components pass the quality hook.
- [ ] Local named components and inline `component`, `errorComponent`, or
      `notFoundComponent` callbacks in ordinary routes fail the hook.
- [ ] The root Router shell continues to pass.
- [ ] The dashboard route stays functional and its route entry is thin.
- [ ] Hook tests, frontend static checks, browser regression checks, quality
      hooks, and `git diff --check` pass with no generated-file diff.

## Notes

- This is a maintenance task; no public API or route URL changes are in scope.
