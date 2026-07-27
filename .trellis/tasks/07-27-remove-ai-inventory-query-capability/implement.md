# Implementation plan

## 1. Task and documentation setup

- Add the implementation note to `docs/decisions/AI_CHANGELOG.md`.
- Add the AI capability-removal note to `.trellis/spec/log.md`.
- Remove `.trellis/spec/ai-sidecar-contract.md` and its entry from
  `.trellis/spec/index.md`.
- Archive the active AI parent/frontend/evaluation tasks with a superseded note
  using `task.py archive --no-commit`, children before parent.

## 2. Database and backend removal

- Add the removal migration with current head `8c4d1e7a2b5f` as its parent.
- Add migration-focused tests or a repeatable isolated-database check for
  upgrade, downgrade-to-prior-head, and re-upgrade behavior.
- Remove AI modules, schemas, models, route registration, config fields and
  validators, AI-only exception, fixtures, and AI tests.
- Remove AI-specific observability threshold/dependency and only its focused
  tests, preserving generic observability coverage.

## 3. Sidecar, deployment, and configuration removal

- Delete tracked `sidecar/**` source/tests/package/Dockerfile.
- Remove the `sidecar` workspace from root `package.json` and regenerate
  `bun.lock` with the remaining frontend workspace.
- Remove the Compose sidecar service and all AI environment mappings from every
  service, then remove AI values from `.env` and `.env.production.example`.
- Remove the `.env.ai.secrets` ignore rule and both AI operation guides; clean
  `docs/README.md` links.

## 4. OpenAPI and generated client synchronization

- Run `bash ./scripts/generate-client.sh` after backend route removal.
- Copy/synchronize the generated `frontend/openapi.json` to the tracked root
  `openapi.json` if it differs.
- Review generated `frontend/src/client/**` changes and verify only AI symbols
  disappear; do not hand-edit generated files.

## 5. Verification and delivery

- Run isolated backend tests with `POSTGRES_DB` ending in `_test` or `_pytest`.
- Run backend `mypy`, `ty`, Ruff check/format checks and frontend Biome CI/build.
- Parse/validate Compose configuration and search for forbidden runtime AI
  references, allowing only ADR/archive/history records.
- Review the complete diff for unrelated changes, then record task progress and
  commit the scoped implementation and Trellis updates.

## Rollback points

- Before migration testing: backend source and generated client can be restored
  without touching unrelated migrations.
- Before task archival: runtime deletion can be reviewed independently from
  Trellis metadata changes.
- The database removal migration's downgrade recreates empty schema only; it is
  not a data-recovery mechanism.
