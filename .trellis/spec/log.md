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
