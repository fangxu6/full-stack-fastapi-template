# Trellis Spec Maintenance Log

> Append-only log for durable changes under `.trellis/spec/**`.

---

## 2026-07-17

- Added the AI inventory sidecar contract. It freezes the private BFF endpoint,
  two separate service tokens, five-tool allowlist, structured result/error
  envelopes, `gpt-5.6-luna` with medium reasoning, private Docker networking,
  and allowlisted operational logs.
- Source inputs: `sidecar/**`, `compose.yml`, and
  `.trellis/tasks/07-16-mastra-inventory-orchestrator/`.
- Recorded the FastAPI client implementation: separate orchestration token,
  30-second no-retry request, completed-run provider/model audit, and
  fail-before-503 behavior for unavailable or invalid sidecar responses.

## 2026-07-15

- Added the frontend pagination contract for Ant Design 6 server-side lists.
  It defines one-based UI pages mapped to the current `skip` / `limit` API,
  requires `data + count` responses, makes `current`, `pageSize`, and `total`
  controlled state, and prevents duplicate client-side/server-side pagination.
- Added query-key, page-reset, deletion-recovery, error/empty-state, and test
  requirements for paginated lists. `Pagination.onChange` is the single state
  transition for both page and page-size changes; a page-size change resets the
  selected page to `1` because Ant Design does not do so automatically.
- Hardened the existing Items offset-paging endpoint: the route rejects
  `skip < 0`, `limit < 1`, and `limit > 100` with the shared validation error
  contract, while the CRUD query orders by `created_at DESC, id DESC` for a
  stable page boundary. Added focused API and CRUD regression coverage.
- Source inputs: Ant Design 6.5 Pagination official docs,
  `frontend/package.json`, `frontend/src/shared/components/table/DataTable.tsx`,
  `frontend/src/features/items/pages/ItemsPage.tsx`,
  `backend/app/api/routes/items.py`, `backend/app/schemas/item.py`, and the
  generated Items client.

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

## 2026-07-10

- Superseded the earlier item module-route experiment for this CRUD-heavy
  project: simple CRUD should stay lightweight on
  `api/routes -> services -> crud -> ORM`, while `modules/*` is reserved for
  domains with multi-table workflows, state transitions, background tasks,
  events, external-system calls, or cross-module collaboration.
- Source inputs: `3. Python后端架构规则-ORM隔离与实用边界.md`,
  `backend/app/api/routes/items.py`, `backend/app/services/item.py`,
  `backend/app/crud/item.py`, focused item tests, and generated OpenAPI client
  output.

## 2026-07-11

- Added the project quality-hook contract: a typed project-owned interface,
  registry, explicit CLI, and regression requirements for backend/frontend
  policies without modifying Trellis library files.
- Recorded Windows backend-gate execution through the repository virtual
  environment because WSL Bash does not inherit that environment reliably.
- Source inputs: `hooks/quality_hooks/**`, `hooks/run_quality_hooks.py`, and
  `hooks/tests/test_quality_hooks.py`.
- Added the project-local Codex `Stop` adapter. It maps a failed quality-hook
  CLI run to Codex `decision: block` output, so a failing quality gate creates
  a continuation prompt rather than allowing the turn to finish.
- Source inputs: `.codex/hooks.json`, `.codex/hooks/stop-quality-gate.py`, and
  `hooks/tests/test_stop_quality_gate.py`.
