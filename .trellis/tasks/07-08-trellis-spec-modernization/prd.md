# Plan Trellis spec modernization

## Goal

Plan the modernization of this project's `.trellis/spec/**` so it keeps the current FastAPI/React repo grounding while adopting the more mature, technology-neutral specification patterns found in `.trellis-other/spec`.

The outcome should be a reviewed implementation plan for improving the spec system, not an immediate rewrite and not a copy of JSE_AI_Speckit business rules.

## Background

The comparison document at `docs/trellis-spec-diff-analysis.md` found that:

- current `.trellis/spec` has 17 Markdown files and about 1634 lines;
- `.trellis-other/spec` has 60 Markdown files and about 9036 lines;
- `.trellis-other/spec` is much richer because it has a global catalog, maintenance log, scenario contracts, validation matrices, explicit test requirements, wrong-vs-correct examples, and quality gates;
- the richer parts are mostly reusable as a spec-writing method, but JSE/PMS/Tooling/Vue/MySQL/runtime assumptions must not be copied into this project.

## Requirements

1. Use `docs/trellis-spec-diff-analysis.md` as the source analysis for the modernization plan.
2. Preserve current project reality:
   - FastAPI + SQLModel backend under `backend/app/**`
   - React + Vite frontend under `frontend/src/**`
   - generated OpenAPI client under `frontend/src/client/**`
   - Docker Compose/backend 8000/frontend 5173 validation assumptions
3. Do not copy JSE_AI_Speckit business-specific spec content, including PMS, Tooling, Training, SQDM, WXWork, JSECommon paths, Vue/Element Plus conventions, MySQL/BINARY UUID rules, pm2, or port 9000 assumptions.
4. Plan additions for technology-neutral spec capabilities:
   - global spec catalog and maintenance log
   - scenario contract template
   - trigger-based Read Order entries
   - stronger backend/frontend quality gates
   - backend type-safety guideline
   - additions to code-reuse and cross-layer thinking guides
5. Define which files under `.trellis/spec/**` should be created or edited.
6. Define validation commands and review checks before implementation starts.

## Acceptance Criteria

- [ ] `design.md` maps each proposed spec modernization area to concrete current-project files.
- [ ] `implement.md` contains an ordered checklist for updating `.trellis/spec/**` safely.
- [ ] The plan explicitly distinguishes "reuse the pattern" from "copy the JSE/PMS content".
- [ ] The plan includes validation for markdown links, placeholder/stale-template scans, and `git diff --check`.
- [ ] The task remains in `planning` until the user reviews the plan and asks to start implementation.

## Out Of Scope

- Editing `.trellis/spec/**` before plan review.
- Importing `.trellis-other/spec/**` wholesale.
- Copying JSE/PMS/Tooling domain contracts into this repository.
- Changing application code outside Trellis docs/specs.
