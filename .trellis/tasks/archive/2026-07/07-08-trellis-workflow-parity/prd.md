# Plan Trellis workflow parity

## Goal

Create a reviewed plan for adapting the useful `workflow.md` improvements seen in `.trellis-other` to this local FastAPI/React project, while removing JSE_AI_Speckit-specific assumptions.

The later implementation should modernize `.trellis/workflow.md` for this repository's actual runtime, validation paths, and Codex inline workflow instead of copying the JSE/PMS workflow text verbatim.

## Background

Prior comparison found that `.trellis-other/workflow.md` included several workflow features that are not currently in this project's `.trellis/workflow.md`:

- `grill-with-docs` as a planning stress-test path for risky or complex tasks
- `e2e-api-tests.md` as a required planning artifact for API-facing or cross-layer complex tasks
- `spec_wiki.py index`, `spec_wiki.py lint`, and `spec_wiki.py log` as the spec catalog and maintenance loop
- local API E2E expectations against `http://127.0.0.1:9000`
- pm2 process recovery through `fastapi-app`

Local project inspection shows those runtime assumptions need adaptation:

- The backend local healthcheck in `compose.yml` targets container port `8000` at `/api/v1/utils/health-check/`.
- `compose.override.yml` maps backend `8000:8000` and frontend `5173:80`.
- Frontend Playwright uses `http://localhost:5173`.
- Existing test scripts use Docker Compose (`scripts/test.sh`, `scripts/test-local.sh`) rather than pm2.
- Current `.trellis/workflow.md` uses `python`, Codex inline mode, and the existing FastAPI/React Trellis specs.

## Requirements

1. Compare the current `workflow.md` against the desired feature set and classify each `.trellis-other` workflow addition as:
   - adopt directly
   - adopt with local FastAPI/React adaptation
   - reject as JSE/PMS-specific
2. Adapt local E2E guidance to this project:
   - backend default: `http://localhost:8000` / `http://127.0.0.1:8000`
   - health endpoint: `/api/v1/utils/health-check/`
   - frontend default: `http://localhost:5173`
   - stack management: Docker Compose, not pm2
3. Decide how `e2e-api-tests.md` fits this repository:
   - require it for API-facing or cross-layer complex tasks
   - include endpoint, setup data, payload, response, persistence, and failure-side-effect expectations
   - ensure Phase 2 quality checks reference it when present
4. Decide how `grill-with-docs` fits this repository:
   - use it for complex, risky, ambiguous, architecture, API, data model, or cross-layer planning
   - keep lightweight tasks PRD-only when appropriate
5. If `spec_wiki.py` is imported by the helper-script task, update the workflow to describe `index`, `lint`, and `log` maintenance using this project's `.trellis/spec/**`.
6. Preserve workflow breadcrumb invariants:
   - every new required step must be reflected in the matching `[workflow-state:*]` block
   - Codex inline blocks must remain inline and must not instruct sub-agent dispatch
7. Do not copy JSE-specific references such as PMS, Tooling, port `9000`, pm2 `fastapi-app`, or JSE-specific API paths into this repository.

## Acceptance Criteria

- [ ] `design.md` maps each desired `.trellis-other` workflow addition to a local decision: adopt, adapt, or reject.
- [ ] `implement.md` contains an ordered checklist for safely editing `.trellis/workflow.md`.
- [ ] The plan explicitly replaces JSE `9000`/pm2 guidance with this repo's Docker Compose `8000` backend and `5173` frontend flow.
- [ ] The plan includes validation commands for `get_context.py --mode phase`, breadcrumb tag presence, markdown sanity, and any `spec_wiki.py` references if adopted.
- [ ] The task remains in `planning` until the user reviews the plan and asks to start implementation.

## Out Of Scope

- Editing `.trellis/workflow.md` before plan review.
- Importing JSE/PMS/Tooling business rules.
- Replacing the current workflow wholesale.
- Changing application code outside Trellis workflow/docs.
