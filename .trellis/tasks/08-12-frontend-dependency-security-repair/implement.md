# Implementation Record: Frontend Dependency Security Repair

## Execution Order

1. Remove and ignore the accidental `package-lock.json`.
2. Upgrade Axios with Bun and test the OpenAPI generator upgrade in isolation.
3. Keep the generator's Dependabot ignore rule while its migration is deferred.
4. Run client generation and inspect its complete diff.
5. Run focused and full frontend quality checks, then Docker/E2E checks when
   the local environment permits.
6. Run reproducible audit commands and record both results and limitations.
7. Write the operations runbook before final review, including the generator
   rollback and remaining audit risk.

## Actual Results

- Axios upgrade succeeded: `1.16.0` -> `1.19.0`.
- Generator `0.99.0` test failed safely: it reported `0 files` and removed the
  existing generated output before the normalization step failed.
- Generated output was restored and generator `0.73.0` was reinstalled.
- Dependabot's generator ignore remains deliberate pending a migration task.
- `bun audit` is blocked by the configured mirror returning HTTP 404.

## Validation

```text
bun ci
bun run --filter frontend build
bun run --filter frontend lint
cd frontend && bun test src/app/query-retry.test.ts
bash scripts/generate-client.sh
docker compose build
docker compose up -d --wait backend
cd frontend && bunx playwright test --project=chromium
```

Recorded validation:

- `bun ci` passed.
- `bash scripts/generate-client.sh` passed with `@hey-api/openapi-ts@0.73.0`;
  generated output was unchanged after the failed 0.99.0 experiment was
  rolled back.
- `bun run --filter frontend build` passed.
- `bun run --filter frontend lint` passed with exit code 0; Biome 2.4.16 vs
  config metadata 2.3.14 was informational only.
- `bun test src/app/query-retry.test.ts` passed: 3 tests, 29 assertions.
- `python hooks/run_quality_hooks.py --json` and `git diff --check` passed.
- `docker compose build frontend` and Docker-backed Playwright validation are
  blocked because `docker` is absent from `PATH`.
- Official-registry fallback audit: production (`--omit=dev`) has 0
  vulnerabilities; full development audit has 5 vulnerabilities, all from
  the deferred generator chain.

## Rollback

Revert the dependency, generated-client, ignore-rule, and documentation commits
together. Do not restore `package-lock.json` as a tracked file.
