# Clean Up Legacy Thick Routes

## Goal

Remove the two remaining local route adapter components so every ordinary
frontend route entry follows the thin-route boundary already enforced for new
changes.

## Confirmed Facts

- `frontend/src/routes/_layout/rules.tsx` declares `RulesRoute` only to pass
  validated `slug` search state to `RulesPage`.
- `frontend/src/routes/reset-password.tsx` declares `ResetPasswordRoute` only
  to pass validated `token` search state to `ResetPasswordPage`.
- The AST checker reports exactly those two ordinary routes as violations;
  `routes/__root.tsx` is the documented Router-shell exception.
- `ForbiddenPage` already reads validated route search state in its page module
  through TanStack Router's typed `useSearch({ from })` pattern.

## Requirements

1. Make the two route entries import their page component directly and contain
   no local page adapter component.
2. Move each page's search-state consumption into its owning platform page
   module using its existing route ID.
3. Preserve route URLs, search validation, redirects, metadata, permissions,
   generated route tree, and user-visible reset-password and rules behavior.
4. Add a regression that verifies the complete current route inventory passes
   the thin-route AST policy.

## Acceptance Criteria

- [ ] `rules.tsx` and `reset-password.tsx` have no local PascalCase component
      declaration and use imported page components directly.
- [ ] `RulesPage` preserves selected/default rule behavior for `slug` search.
- [ ] `ResetPasswordPage` preserves the validated reset-token submission flow.
- [ ] The AST checker reports no violations for all ordinary current route
      entries, while retaining the root-shell exception.
- [ ] Existing reset-password browser coverage, frontend type/Biome checks,
      quality hooks, and `git diff --check` pass.

## Out Of Scope

- New routes, URL changes, route-tree regeneration, backend/API changes,
  navigation or permission changes, and broad page refactors.
