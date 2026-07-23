# Implementation Plan: Route Legacy Cleanup

1. Add a failing AST inventory regression that scans all current route entries
   and expects no violations.
2. Move `slug` search-state reading into `RulesPage`; simplify the rules route
   to a direct imported component reference while preserving schema and head.
3. Move `token` search-state reading into `ResetPasswordPage`; simplify the
   reset-password route while preserving schema, redirects, and head.
4. Run the AST test, complete AST CLI inventory, frontend type check, read-only
   Biome, quality hooks, and `git diff --check`.
5. Run the existing reset-password Playwright suite against the isolated local
   test stack; if unavailable, record the concrete environment blocker.

## Validation Record

- The local frontend was listening on port 5173, but no API listener was
  available on 8000 and no MailCatcher listener was available on 1025 or 1080.
  The end-to-end reset-password suite therefore cannot exercise its email-link
  flow in this session without provisioning those external test services.

## Rollback Points

- Revert either page/route pair independently if its route-search binding
  regresses.
- Revert the inventory regression with the AST-policy change only if the
  policy itself must be relaxed; do not weaken it for a route adapter.
