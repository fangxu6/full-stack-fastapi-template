# Design: Trellis workflow parity

## Design Principle

Use `.trellis-other/workflow.md` as a feature reference, not as source text to copy. The implementation should express the same useful workflow mechanics in the language of this project: FastAPI + SQLModel backend, React/Vite frontend, Docker Compose local stack, and Codex inline execution.

## Addition Matrix

| `.trellis-other` addition | Local decision | Local adaptation |
| --- | --- | --- |
| `grill-with-docs` planning pass | Adopt with adaptation | Add as an optional/required planning stress-test for complex, risky, ambiguous, API, data, or cross-layer tasks. Do not require it for small PRD-only tasks. |
| `e2e-api-tests.md` artifact | Adopt with adaptation | Require for API-facing or cross-layer complex tasks. Reference it in Planning Artifacts, Phase 1.1, Phase 1.4, Phase 2.1/2.2, and inline breadcrumbs. |
| `spec_wiki.py index/lint/log` loop | Conditional adopt | Add only if the helper-script parity task imports and validates `spec_wiki.py`. Otherwise phrase as future/when-available guidance or defer. |
| Local API E2E at `127.0.0.1:9000` | Reject literal value | Replace with local backend `http://localhost:8000` / `http://127.0.0.1:8000` and health endpoint `/api/v1/utils/health-check/`. |
| pm2 `fastapi-app` restart | Reject | Replace with Docker Compose commands, such as `docker compose up -d backend`, `docker compose restart backend`, and existing `scripts/test.sh` flow after verification. |
| JSE/PMS/Tooling domain text | Reject | Keep workflow generic and aligned with this FastAPI/React template project. |

## Local Runtime Evidence

- `compose.override.yml` maps backend `8000:8000` and frontend `5173:80`.
- `compose.yml` backend healthcheck uses `http://localhost:8000/api/v1/utils/health-check/` inside the container.
- `frontend/playwright.config.ts` uses `http://localhost:5173`.
- `scripts/test.sh` builds and runs the Docker Compose stack, then executes backend tests inside the backend container.
- No local workflow evidence supports pm2 or `fastapi-app`.

## Workflow Sections To Update

1. Core Principles:
   - Add a principle for stress-testing risky plans only if it stays concise and non-project-specific.
2. Spec System:
   - If `spec_wiki.py` exists after helper-script import, document `index`, `lint`, and `log`.
   - Keep current `.trellis/spec/**` FastAPI/React guidance as the source of truth.
3. Planning Artifacts:
   - Add `e2e-api-tests.md` as required for API-facing or cross-layer complex tasks.
4. Phase Index:
   - Update Phase 1 summary to mention grill and E2E planning when applicable.
   - Update Phase 2 summary to mention planned validation including E2E tests when present.
5. Breadcrumb Blocks:
   - `planning` and `planning-inline`: mention `grill-with-docs` when task complexity warrants it and `e2e-api-tests.md` for API-facing complex tasks.
   - `in_progress` and `in_progress-inline`: mention reading/running `e2e-api-tests.md` when present.
6. Detailed Phase 1:
   - Explain when to create `e2e-api-tests.md`.
   - Explain when to run a grill pass.
7. Detailed Phase 2:
   - Include local Docker Compose E2E validation expectations.
8. Detailed Phase 3:
   - If `spec_wiki.py` is adopted, add catalog/log/lint maintenance to the spec update step.

## Compatibility Notes

- Keep commands as `python` unless the local scripts or Windows environment require `python3`.
- Keep Codex inline instructions explicit: do not dispatch implement/check sub-agents in inline mode.
- If local E2E requires a running stack, the workflow should first check Docker Compose availability and health before declaring tests skipped.
- Avoid making every task heavier. The workflow should preserve the PRD-only path for lightweight tasks.

## Rollback

Rollback is a single-file revert of `.trellis/workflow.md` plus any optional generated `.trellis/spec/index.md` or `.trellis/spec/log.md` changes if `spec_wiki.py` is included. No application code should be touched.
