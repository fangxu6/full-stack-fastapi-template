# Implementation Plan: RBAC Review Findings Repair

1. Add a focused service regression test that distinguishes retained inactive
   role IDs from newly assigned inactive role IDs; run it and confirm RED.
2. Repair the role replacement validation and confirm the focused service test
   is green while the final-administrator test remains green.
3. Update the test fixture to upgrade only an already-validated isolated test
   database before `init_db`; run the previously failing focused pytest command.
4. Replace incompatible schema configuration declarations and type the
   permission dependency factory; run backend lint to verify green.
5. Add a frontend unit test for permission-query error classification; confirm
   RED, then add the classifier, reason-specific state in the existing
   authenticated forbidden page, and guard redirects until green. Keep the
   route entry thin and do not change route topology or the generated route
   tree.
6. Add the generated-client whitespace normalizer to the generator script,
   invoke the generator, and verify `git diff --check` is green.
7. Add a quality-hook regression test for a deleted frontend component path,
   then skip deleted paths before component-policy evaluation and preserve the
   thin-route restriction for existing route entries.
8. Run targeted backend tests, backend lint, frontend unit tests, TypeScript
   build, read-only Biome check, task E2E cases, quality hooks, and final diff
   checks.

## Rollback Points

- Revert the service validation plus its test together.
- Revert the test fixture migration bootstrap independently if a test-runtime
  policy requires external migration orchestration instead.
- Revert the guard error pages and generated-client helper independently; they
  do not require a database rollback.
