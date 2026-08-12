# Design: Frontend Dependency Security Repair

## Boundaries

`frontend/package.json` and root `bun.lock` are the dependency source of
truth. Docker and CI both consume Bun. `package-lock.json` is an accidental
local npm artifact and must not coexist with the Bun lock.

The application runtime boundary is Axios. The development-only boundary is
`@hey-api/openapi-ts`, which generates `frontend/src/client/**` through
`scripts/generate-client.sh`. The generated Axios transport remains owned by
the generator configuration, not hand-written source.

## Upgrade Strategy

Upgrade Axios explicitly. Test the generator upgrade in the existing
configuration, but treat any generated-output deletion or plugin incompatibility
as a hard rollback condition. The existing app-level retry interceptor is the
regression boundary because it consumes generated Axios response types.

`@hey-api/openapi-ts@0.99.0` is deferred after testing showed that the legacy
plugin configuration produced no files. The vulnerable generator chain remains
a documented development-only risk until that migration is completed.

## Security Verification

The configured `registry.npmmirror.com` returns 404 for Bun's audit endpoint.
The runbook records this limitation and supplies an official-registry npm audit
in a disposable directory as the reproducible verification fallback. That
temporary lockfile is never copied into the repository.

## Rollback

Restore the manifest, Bun lock, Dependabot configuration, generated client,
and documentation from the task commits. No data, API, or deployment rollback
is required.
