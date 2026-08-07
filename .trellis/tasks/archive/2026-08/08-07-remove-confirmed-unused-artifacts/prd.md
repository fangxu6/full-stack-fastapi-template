# Remove Confirmed Unused Repository Artifacts

## Goal

Remove repository artifacts and dependency entries that have no current runtime
consumer, while preserving the explicitly retained cache foundation, UI
primitives, and PM2 development logging path.

## Confirmed Facts

- The user explicitly wants `backend/app/core/cache.py` retained.
- The user explicitly wants these UI primitives retained:
  `alert.tsx`, `card.tsx`, `pagination.tsx`, and `button-group.tsx`.
- PM2 is used only for local development in the current workflow. Its
  `ecosystem.config.js` and `scripts/pm2-json-prefix.cjs` are in scope for
  preservation, not deletion.
- `frontend/openapi.json` is an ignored generated file consumed by the frontend
  client generator; the tracked root `openapi.json` has no current source or
  build consumer.

## Requirements

- Delete the five dated root `architecture-review-*.html` snapshots.
- Delete the tracked root `openapi.json`, keeping the ignored frontend-generated
  OpenAPI input and its generation script unchanged.
- Remove the five frontend dependencies with no non-lockfile source reference:
  `@tanstack/router-devtools`, `@radix-ui/react-radio-group`,
  `@radix-ui/react-scroll-area`, `form-data`, and `react-error-boundary`.
- Update `bun.lock` consistently with the dependency removal.
- Remove the unused `backend/app/core/logging.py` shim.
- Consolidate the duplicate test database readiness entrypoint by removing
  `backend/app/tests_pre_start.py`, pointing `backend/scripts/tests-start.sh`
  at `backend_pre_start.py`, and removing its duplicate test.
- Do not modify or delete the cache module, the four retained UI primitives,
  PM2 configuration/wrapper, generated frontend client, or cache guidance.

## Acceptance Criteria

- [ ] The listed artifacts and only the listed artifacts are deleted or updated.
- [ ] No tracked source, active documentation, script, or package manifest
      references a deleted runtime file or removed dependency.
- [ ] The retained cache, UI, PM2, and OpenAPI generation paths remain present.
- [ ] Backend readiness and PM2 wrapper focused tests pass.
- [ ] Frontend dependency installation/build validation passes.
- [ ] The working tree diff contains no unrelated changes.

## Out of Scope

- Reworking PM2 paths, development process definitions, or log formatting.
- Removing Redis cache code or its tests/specification.
- Removing the four retained UI primitives or their Radix/runtime support.
- Changing API schemas, generated client code, backend behavior, or production
  deployment configuration.

## Open Questions

None. The deletion boundary is explicitly approved by the user; implementation
still requires the final planning-summary approval gate.
