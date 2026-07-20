# Design: Trellis spec modernization

## Design Principle

Modernize the spec system by importing the shape of the stronger rules, not the source project's business content. Every final rule must be grounded in this repository's FastAPI/React code, local docs, and existing `.trellis/spec/**` files.

## Source Inputs

- `docs/trellis-spec-diff-analysis.md`
- current `.trellis/spec/**`
- `.trellis-other/spec/**` as a reference for structure only
- current backend/frontend code and config when verifying concrete rules

## Proposed Spec Changes

| Area | Current state | Proposed modernization |
| --- | --- | --- |
| Spec catalog | No `.trellis/spec/index.md` | Add a current-project catalog once `spec_wiki.py` is available or create a manually maintained catalog as an interim step. |
| Spec log | No `.trellis/spec/log.md` | Add an append-only log for spec updates, lint passes, and task-derived lessons. |
| Scenario contracts | Mostly one current example: `frontend/route-permission-navigation-contract.md` | Standardize a scenario contract template and use it for high-risk cross-layer rules. |
| Backend quality | Has solid baseline but limited delivery gates | Add file-size guidance, why/invariant comments, N+1/batch checks, OpenAPI/client/document sync checks. |
| Frontend quality | Has generated-client and route/menu checks | Strengthen route/menu/permission/config consistency, UI error-state checks, generated-client usage checks. |
| Backend type safety | No dedicated file | Add `backend/type-safety.md` for SQLModel/Pydantic, UUID, datetime, nullable, schema, and service signature rules grounded in this repo. |
| Read order | Mostly base layer order | Add trigger-based routing: schema/API changes, error changes, permission/nav changes, generated-client changes, cross-layer work. |
| Code reuse guide | Strong local guide already | Add batch-change backcheck and asymmetric-mechanism drift gotcha. |
| Cross-layer guide | Strong local guide already | Add generic Source -> Transform -> Store -> Retrieve -> Display framing while preserving FastAPI/OpenAPI/React specifics. |

## Candidate New Files

- `.trellis/spec/index.md`
- `.trellis/spec/log.md`
- `.trellis/spec/templates/scenario-contract-template.md` or a guide section if templates are not desired
- `.trellis/spec/backend/type-safety.md`
- optional future contracts:
  - `.trellis/spec/backend/openapi-client-regeneration-contract.md`
  - `.trellis/spec/backend/unified-error-request-id-contract.md`
  - `.trellis/spec/frontend/auth-current-user-state-contract.md`

## Candidate Edited Files

- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/quality-guidelines.md`
- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/quality-guidelines.md`
- `.trellis/spec/guides/index.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`

## Reuse vs Reject Rules

Reusable from `.trellis-other/spec`:

- catalog/log mechanism
- scenario contract sections
- trigger-based read order
- validation matrix
- good/base/bad cases
- tests required
- wrong-vs-correct examples
- file size and commenting quality gates
- batch/N+1/config consistency thinking

Rejected from `.trellis-other/spec`:

- PMS, Tooling, Training, SQDM, WXWork domain rules
- JSECommon/JSE_UI_AI path assumptions
- Vue/Pinia/Element Plus/JSE compact UI rules
- MySQL/Celery/Redis/Loguru/BINARY UUID specifics
- pm2/9000/5174 runtime assumptions
- `/home/hq/workspaces/.venv/bin/` environment assumptions

## Validation Strategy

- Check all local markdown links under `.trellis/spec/**`.
- Search for forbidden imported terms: `JSE`, `PMS`, `Tooling`, `SQDM`, `WXWork`, `9000`, `5174`, `pm2`, `BINARY(16)`, `/home/hq/workspaces`.
- Search for stale placeholders such as `TBD`, `TODO`, `template`, and unverifiable generic claims.
- Run `git diff --check -- .trellis/spec`.
- If `spec_wiki.py` is available, run `python ./.trellis/scripts/spec_wiki.py index` and `python ./.trellis/scripts/spec_wiki.py lint`.

## Rollback

All implementation should be confined to `.trellis/spec/**` and this task directory. Rollback is reverting those files from the implementation diff. Do not touch application code.
