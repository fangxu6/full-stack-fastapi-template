# Refresh Trellis Specs Design

## Scope

Update the Trellis spec tree under `.trellis/spec/**`:

- `.trellis/spec/guides/**`
- `.trellis/spec/backend/**`
- `.trellis/spec/frontend/**`

Product code is read-only evidence for this task. The task may update only
planning artifacts and spec documents.

## Evidence Sources

Primary sources:

- CodeGraph exploration of backend architecture, exception flow, models,
  schemas, services, generated frontend client usage, route guards, menu
  components, page placement, and auth/query behavior.
- Current Trellis specs and indexes.
- Project config files: `backend/pyproject.toml`, `frontend/package.json`,
  `frontend/biome.json`, `frontend/vite.config.ts`,
  `scripts/generate-client.sh`.
- Project docs: `README.md`, `development.md`.

## Spec Structure

Keep the existing two-layer structure:

```text
.trellis/spec/
├── backend/
├── frontend/
└── guides/
```

This matches `get_context.py --mode packages`, which reports a single-repo
project with backend and frontend spec layers.

## Backend Guidance Shape

Backend specs should preserve the current architecture facts:

- `api/*` owns HTTP routing and dependency wiring.
- `services/*` owns business rules and orchestration.
- `crud/*` owns persistence helpers.
- `models/*` and `schemas/*` split storage models and API contracts.
- `core/*` owns cross-cutting platform behavior.
- `modules/*` and `infra/*` are present but still mostly boundary skeletons.

Backend specs should explicitly protect:

- unified `detail + request_id` error responses
- `X-Request-ID` propagation
- server-side traceback logging for unhandled exceptions
- UUID identifiers, UTC timestamps, `data + count` list wrappers
- Alembic review for model changes
- frontend client regeneration for OpenAPI contract changes

## Frontend Guidance Shape

Frontend specs should preserve the current boundary model:

- `routes/*` stays thin and delegates to page modules.
- `app/*` owns layout, navigation, and guards.
- `platform/*` owns auth/system/cross-business capabilities.
- `features/*` owns business feature pages and components.
- `shared/*` is admitted only for reusable components/helpers.
- `frontend/src/client/**`, `frontend/src/routeTree.gen.ts`, and
  `frontend/src/components/ui/**` are generated or vendor-style files and should
  not be manually edited for normal feature work.

Frontend specs should explicitly protect:

- generated OpenAPI client as the API type source
- React Query for server state and mutation invalidation
- `useAuth` as the current auth/token/current-user boundary
- route guard, permission helper, and menu visibility alignment
- Biome/Vite/TanStack Router/Bun validation commands

## Shared Guide Changes

The shared guides should remain practical thinking tools, but examples must be
from this FastAPI/React repository. Current references to Trellis runtime
template upgrade mechanics are not appropriate as project coding guidance here
and should be replaced with backend/frontend cross-layer checks.

## Validation

After edits:

- scan `.trellis/spec/**` for placeholders and stale template markers
- check that all linked spec files still exist
- run `git diff --check`
- inspect `git diff -- .trellis/spec .trellis/tasks/06-30-refresh-codebase-specs`
