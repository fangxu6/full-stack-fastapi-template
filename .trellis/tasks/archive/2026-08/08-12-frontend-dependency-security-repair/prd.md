# Repair Frontend Dependency Security

## Goal

Remove the known runtime Axios and development-time OpenAPI generator
vulnerabilities while retaining Bun as the sole tracked frontend dependency
resolution path.

## Confirmed Current State

- `frontend/package.json` pins `axios` at `1.16.0` and
  `@hey-api/openapi-ts` at `0.73.0`.
- `npm audit` reports Axios vulnerabilities plus transitive `handlebars`,
  `c12`, `giget`, and `tar` vulnerabilities from the generator.
- Docker and CI use `bun ci` and `bun.lock`; `package-lock.json` was removed
  by the prior Bun migration and was recreated locally by an npm command.
- The generator uses `legacy/axios`, `@hey-api/sdk`, and `@hey-api/schemas`.

## Requirements

1. Upgrade Axios to `1.19.0` using Bun. Evaluate OpenAPI TypeScript `0.99.0`
   separately and do not merge it when the existing generator contract breaks.
2. Delete and ignore `package-lock.json`; do not commit a second lockfile.
3. Preserve the existing generator configuration unless the upgraded generator
   proves it incompatible; do not hand-edit generated client files.
4. Regenerate and review `frontend/src/client/**`, then preserve current
   request, interceptor, cancellation, retry, and error behavior.
5. Keep the Dependabot ignore entry for `@hey-api/openapi-ts` until its
   dedicated plugin migration is complete.
6. Record every command, outcome, and environment blocker in an operations
   runbook suitable for manual future execution.
7. Do not use `npm audit fix --force`, dependency overrides, backend changes,
   or unrelated dependency upgrades.

## Acceptance Criteria

- [x] `axios` is `1.19.0` in the frontend manifest and Bun lockfile.
- [x] `@hey-api/openapi-ts@0.99.0` was tested and rolled back because the
      existing config generated 0 files and removed the client output.
- [x] `package-lock.json` is deleted and ignored.
- [x] The generator compatibility blocker and rollback are recorded.
- [x] Generated-client generation succeeds with the restored compatible
      generator and produces no unreviewed client diff.
- [x] Frontend build, lint, focused retry tests, and quality hooks have
      concrete recorded results; Docker/E2E blockers are recorded.
- [x] Security audit results and the configured registry limitation are
      recorded with reproducible commands.
- [x] Dependabot continues to ignore the generator pending its migration.

## Out Of Scope

- Changing backend API contracts, request retry behavior, or application UI.
- Switching the repository from Bun to npm or changing Docker runtime images.
- Unrelated package upgrades and manual patches to generated files.

## Deferred Generator Migration

`@hey-api/openapi-ts@0.99.0` is deferred to a separate migration task. Its
current CLI accepted the legacy config but generated `0 files`, after which
the existing normalization script failed because `frontend/src/client` was
gone. The migration must map `legacy/axios` to the supported client plugin and
review all generated exports and transport behavior.
