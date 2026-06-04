---
title: LLM-Wiki for R&D automation
created: 2026-06-04
updated: 2026-06-04
type: concept
tags:
  - llm-wiki
  - ai-engineering
  - knowledge-management
status: active
---

# LLM-Wiki for R&D Automation

## Summary

LLM-Wiki for R&D automation treats durable engineering knowledge as a maintained Markdown graph. The goal is to compile stable knowledge at write time so later agents can answer, design, review, test, and troubleshoot with traceable context.

## Repository Mapping

- Sources are existing docs, code, Trellis tasks, specs, and research.
- Wiki pages live under `docs/llm-wiki/`.
- Skills under `.agents/skills/kb-*` route agents through wiki-aware workflows.
- Trellis remains the higher-level harness for task lifecycle and implementation gates.

## Practical Rules

- Start with high-value sources rather than bulk ingesting the whole repository.
- Keep each page traceable to source files.
- Mark inference explicitly.
- Prefer updating existing durable pages over creating duplicate concepts.
- Use evaluation tasks to decide whether a wiki or skill change improves outcomes.

## Sources

- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]
- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]
- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]

