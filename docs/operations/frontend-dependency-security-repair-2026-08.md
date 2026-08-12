# Frontend Dependency Security Repair (2026-08)

## Initial Finding

On 2026-08-12, `npm audit` reported six vulnerabilities: direct `axios@1.16.0`
runtime findings, plus `handlebars`, `c12`, `giget`, and `tar` pulled by
`@hey-api/openapi-ts@0.73.0`. `npm audit fix --force` proposed a breaking
upgrade to `@hey-api/openapi-ts@0.99.0`.

The repository is Bun-managed. Docker and CI run `bun ci` and consume
`bun.lock`; `package-lock.json` was an accidental local npm artifact.

## Commands Executed

```powershell
git status --short
npm audit --json
npm audit --omit=dev
bun pm why axios
bun pm why @hey-api/openapi-ts
bun pm why handlebars
bun pm why tar
bun add --cwd frontend axios@1.19.0
bun add --cwd frontend --dev @hey-api/openapi-ts@0.99.0
```

Results:

- `axios` upgraded to `1.19.0`.
- `@hey-api/openapi-ts@0.99.0` was tested but rolled back: the legacy config
  reported `0 files`, removed `frontend/src/client`, and failed the existing
  normalization step.
- `@hey-api/openapi-ts` remains `0.73.0`; its development-only vulnerable
  transitive chain is deferred to a dedicated generator migration.
- The npm lockfile was deleted and is now ignored; do not recreate it.

## Generator Verification

Run from the repository root after dependency installation:

```bash
bash scripts/generate-client.sh
```

This regenerates `frontend/src/client/**`, normalizes generated whitespace,
and runs Biome on the generated client. Review generated changes as a separate
diff; never hand-edit them. With the restored `0.73.0` generator, this is the
known-compatible path.

Run this script and the repository-wide frontend lint sequentially. The script
redirects OpenAPI output directly to `frontend/openapi.json`; a concurrent lint
can briefly read that file while it is empty and report a false parse failure.

## Deferred Work

Create a separate migration task for `@hey-api/openapi-ts@0.99.0` that maps the
legacy `legacy/axios` plugin to the current client plugin, regenerates the
client, reviews exports and Axios transport behavior, and only then removes the
Dependabot ignore.

## Quality Verification

```powershell
bun ci
bun run --filter frontend build
bun run --filter frontend lint
Push-Location frontend
bun test src/app/query-retry.test.ts
bunx playwright test --project=chromium
Pop-Location
docker compose build
```

Recorded results for this run:

- `bun ci`: passed.
- `bash scripts/generate-client.sh`: passed with the restored compatible
  `@hey-api/openapi-ts@0.73.0`; generated-client diff was empty after restore.
- `bun run --filter frontend build`: passed.
- `bun run --filter frontend lint`: passed with exit code 0. The installed
  Biome is 2.4.16 while the config metadata names 2.3.14; this was an
  informational mismatch only and produced no remaining diff.
- `bun test src/app/query-retry.test.ts` from `frontend/`: 3 tests passed,
  29 assertions.
- `python hooks/run_quality_hooks.py --json`: passed.
- `git diff --check`: passed.
- `docker compose build frontend`: blocked because `docker` is not available
  on `PATH`; no Docker/E2E claim is made from this environment.
- Playwright Docker validation was consequently blocked by the same missing
  Docker runtime.

## Audit Limitation

The configured `bunfig.toml` uses `https://registry.npmmirror.com/`. On this
machine `bun audit` returned HTTP 404 from that registry's audit endpoint.
Record that limitation rather than claiming a clean audit. For a reproducible
follow-up, use the official npm registry in a disposable directory and run:

```powershell
npm install --package-lock-only --ignore-scripts --registry=https://registry.npmjs.org/
npm audit --omit=dev --registry=https://registry.npmjs.org/
npm audit --include=dev --registry=https://registry.npmjs.org/
```

Do not copy the disposable `package-lock.json` into this repository.

The official-registry audit fallback produced:

- `npm audit --omit=dev --registry=https://registry.npmjs.org/`: 0
  vulnerabilities.
- Full development audit: 5 vulnerabilities, all retained through the
  deferred `@hey-api/openapi-ts@0.73.0` chain (`handlebars`, `c12`, `giget`,
  and `tar`).

These are development-only generator risks. Do not run `npm audit fix --force`:
the proposed fix is a breaking generator upgrade whose current legacy config
generates zero files and removes the client output.

## Rollback

Restore `frontend/package.json`, `bun.lock`, Dependabot configuration, and any
generated client diff from the dependency repair commits. Keep the repository
without a tracked npm lockfile.
