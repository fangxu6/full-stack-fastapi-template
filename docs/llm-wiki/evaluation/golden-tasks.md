---
title: LLM-Wiki Golden Tasks
created: 2026-06-04
updated: 2026-06-04
type: evaluation
tags:
  - llm-wiki
  - evaluation
status: active
---

# LLM-Wiki Golden Tasks

Use these tasks to compare baseline answers against wiki-assisted answers after changing `docs/llm-wiki/` or `.agents/skills/kb-*`.

## Backend

1. Explain where a new backend capability should place route, service, schema, model, and error-handling code.
2. Review a backend implementation plan for bypassing shared exception handling and propose corrections.

## Frontend

3. Explain where a new authenticated admin page should live and how the route should stay thin.
4. Review a frontend plan that puts permission logic in a page component and suggest the correct boundary.

## Cross-Layer

5. Draft a technical solution for adding a small user-facing field that flows from PostgreSQL to the React UI.
6. Review a cross-layer change plan for schema/API/client/frontend consistency.

## Troubleshooting

7. Given an error response with `request_id`, describe the expected investigation path across frontend, backend, and logs.

## Documentation Maintenance

8. Decide whether a completed Trellis task should update `.trellis/spec/**`, `docs/llm-wiki/**`, both, or neither.

## Recording Results

For each run, record:

- date
- model/tool
- baseline source set
- wiki-assisted source set
- score by [[docs/llm-wiki/evaluation/rubric|Rubric]]
- observed failure modes
- recommended wiki or skill updates

