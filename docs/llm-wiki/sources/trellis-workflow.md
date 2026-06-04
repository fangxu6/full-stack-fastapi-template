---
title: Trellis workflow source
created: 2026-06-04
updated: 2026-06-04
type: source
tags:
  - llm-wiki
  - trellis
  - workflow
status: active
source_count: 1
---

# Trellis Workflow Source

## Source

- Path: `.trellis/workflow.md`
- Role: Project-managed AI development workflow, task lifecycle, planning artifacts, context routing, implementation, checks, and finish work.

## Key Facts

- Trellis emphasizes plan-before-code, injected specs, persisted knowledge, incremental development, and captured learnings.
- Tasks live under `.trellis/tasks/{MM-DD-name}/` with `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, research, and context manifests.
- Complex tasks need `prd.md`, `design.md`, and `implement.md` before implementation.
- Phase 2 uses implementation and check flows.
- Phase 3 includes final verification, spec update, commit planning, and finish-work reminder.

## Durable Guidance

- Trellis remains the task director for development work.
- LLM-Wiki should not replace `.trellis/tasks/**`.
- Stable lessons from completed tasks should be considered for ingestion into `docs/llm-wiki/`.
- Spec update is the natural point to decide whether wiki maintenance is needed.

## Related Pages

- [[docs/llm-wiki/entities/trellis|Trellis]]
- [[docs/llm-wiki/concepts/spec-driven-development|Spec-driven development]]
- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]

