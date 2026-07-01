# Refresh Trellis specs from codebase

## Goal

Refresh `.trellis/spec/**` so future agents can rely on it as current,
source-backed guidance for this repository. The specs should reflect the real
FastAPI backend, React/Vite frontend, shared cross-layer contracts, and local
verification commands observed in the checkout.

## Confirmed Facts

- The repository is a single-package Trellis project with two spec layers:
  `backend` and `frontend`.
- CodeGraph is available through `.codegraph/` and was used to inspect backend
  and frontend architecture before planning edits.
- Backend code follows an `api -> services -> crud -> models/schemas` flow today,
  with `core/*` owning config, security, exceptions, and request correlation.
- Backend `modules/*` and `infra/*` exist but are still mostly structural
  boundaries; current business behavior remains service-first.
- Backend error handling is centralized through `backend/app/core/exceptions.py`
  and registered from `backend/app/main.py`; error responses must preserve
  `detail`, `request_id`, and `X-Request-ID`.
- Frontend route files are intentionally thin, while page implementations live in
  `platform/*/pages` or `features/*/pages`.
- Frontend auth/query/navigation behavior is centered on `useAuth`,
  `app/router/guards.ts`, `app/navigation/*`, `shared/permissions/*`, React
  Query, and the generated OpenAPI client in `frontend/src/client/**`.
- Tooling facts from current config:
  - backend uses `uv`, Ruff, mypy, `ty`, SQLModel, FastAPI, Alembic, pytest
  - frontend uses Bun, Vite, React 19, TanStack Router, React Query, Tailwind 4,
    Biome 2, Playwright, and `@hey-api/openapi-ts`
  - `scripts/generate-client.sh` generates OpenAPI JSON from the backend, moves
    it to `frontend/openapi.json`, runs the frontend client generator, then runs
    `bun run lint`

## Requirements

- Update current `.trellis/spec/**` files only; do not modify product source
  code unless a broken spec link or task artifact requires it.
- Preserve useful existing rules, but remove or rewrite stale generic/template
  guidance that does not describe this repository.
- Add concrete file anchors and current toolchain facts where they materially
  improve future coding decisions.
- Keep `index.md` files consistent with the final spec file set.
- Keep backend guidance explicit about current reality versus recommended
  direction, especially for `modules/*`, `infra/*`, service-first behavior,
  database contracts, and unified error handling.
- Keep frontend guidance explicit about route/page placement, auth and query
  boundaries, generated-client discipline, Biome exclusions, and route/permission
  synchronization.
- Rewrite shared thinking guides where needed so examples do not describe
  unrelated Trellis CLI/template mechanics as if they were this project's app
  code.

## Acceptance Criteria

- [x] `.trellis/spec/**` contains no placeholder/TBD/template filler text.
- [x] Spec indexes list the files that actually exist after the refresh.
- [x] Backend specs cite real backend files for routing, service, CRUD, model,
      schema, migration, error, logging, and validation guidance.
- [x] Frontend specs cite real frontend files for routes, app shell, page
      placement, auth/query state, generated client usage, Biome/Vite tooling,
      permissions, and navigation.
- [x] Shared guides describe this repository's FastAPI/React cross-layer
      contracts and reuse checks, not unrelated Trellis template update flows.
- [x] Verification includes a placeholder scan, link/path sanity check, and
      `git diff --check`.
