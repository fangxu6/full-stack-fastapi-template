---
name: kb-tech-solution
description: Produce source-backed technical solutions for this repository using docs/llm-wiki, architecture docs, Trellis task artifacts, and code verification. Use when designing features, refactors, cross-layer changes, backend/frontend work, or implementation plans that need project-specific context.
---

# KB Tech Solution

Create a technical solution grounded in the repository knowledge base.

## Required Reads

1. Read `docs/llm-wiki/index.md`.
2. Read relevant wiki pages for architecture, entities, concepts, and syntheses.
3. Read Trellis task artifacts if an active task exists: `prd.md`, `design.md`, `implement.md`.
4. Verify affected code paths or source docs before naming specific files or APIs.

## Workflow

1. Restate the goal and acceptance criteria.
2. Identify impacted layers: backend, frontend, docs, workflow, or cross-layer.
3. Map the change to repository boundaries:
   - backend: `api`, `services`, `crud`, `models`, `schemas`, `core`, `infra`, `modules`
   - frontend: `app`, `platform`, `features`, `shared`, thin `routes`
   - workflow/docs: Trellis task artifacts, `.trellis/spec/**`, `docs/llm-wiki/**`
4. Propose implementation steps with evidence paths.
5. Include risks, rollback shape, and validation commands/scenarios.
6. Identify whether the result should update `.trellis/spec/**`, `docs/llm-wiki/**`, both, or neither.

## Output Rules

- Separate confirmed facts from assumptions.
- Avoid naming code symbols unless verified.
- Keep the plan scoped to the user's requested outcome.
- For cross-layer work, include data flow and error flow.

