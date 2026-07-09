# Trellis Spec Maintenance Log

> Append-only log for durable changes under `.trellis/spec/**`.

---

## 2026-07-08

- Refreshed specs after merging upstream `fastapi/full-stack-fastapi-template`
  `master` into this repository.
- Updated backend runtime/tooling guidance to Python 3.14, FastAPI entrypoint
  configuration, strict mypy, `ty`, Ruff, coverage, and `backend/scripts/*`.
- Updated frontend runtime/tooling guidance to React 19, Vite 8, TanStack Router
  1.170, React Query 5.101, Biome 2.4, and Playwright 1.61.
- Added global spec catalog, maintenance log, scenario contract template, and
  backend type-safety guidance.
- Strengthened backend/frontend quality gates with generated-client, route/menu
  permission, UI state, file-size, comment, batch/N+1, and documentation-sync
  checks.
- Source inputs: current `backend/pyproject.toml`, `frontend/package.json`,
  `scripts/generate-client.sh`, backend/frontend code anchors, and
  `docs/trellis-spec-diff-analysis.md`.

## 2026-07-09

- Recorded Ant Design as a gradual complex-component layer for the React
  frontend, not a replacement for the existing Tailwind + shadcn/ui primitive
  layer.
- Added frontend spec guardrails for Ant Design provider placement, pilot-page
  verification, and the current rejection of `@ant-design/pro-components`.
- Source inputs: `Ant Design：企业级中后台 UI 设计系统.md`, Ant Design 6.5
  official docs, `frontend/package.json`, `frontend/src/main.tsx`, and
  `frontend/src/routes/_layout/rules.tsx`.
- Recorded the backend `items` module pilot: public routes remain under
  `api/routes/items.py`, module-local service/repository behavior lives under
  `modules/items/*`, and item service code owns commit/refresh while item
  repository and `crud.item` helpers do not commit.
- Source inputs: `.trellis/tasks/07-09-backend-items-module-boundary/`,
  `backend/app/api/routes/items.py`, `backend/app/modules/items/service.py`,
  `backend/app/modules/items/repository.py`, and ADR-0002/0003.
