# Implementation Plan: Route Quality Policy

1. Add failing TypeScript tests for valid thin routes, local named components,
   inline component callbacks, and the root-shell exception.
2. Add the AST checker CLI using the installed TypeScript compiler API; make
   the focused tests green.
3. Add failing Python-hook coverage for AST-reported route violations and make
   the hook invoke the checker once per run after filtering deleted paths.
4. Move DashboardPage into the platform layer and reduce the index route to a
   thin import/configuration file.
5. Update frontend quality guidance with the executable route policy.
6. Run hook tests, AST tests, frontend type/Biome checks, focused browser
   checks, the repository quality hooks, and final diff checks.

## Rollback

Revert the checker and hook integration together. The dashboard move can be
reverted independently because it does not alter the route URL or generated
route tree.
