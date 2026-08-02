---
title: Repository AI R&D workflow
created: 2026-06-04
updated: 2026-08-02
type: synthesis
tags:
  - llm-wiki
  - ai-engineering
  - workflow
status: active
source_count: 5
---

# Repository AI R&D Workflow

## Summary

This repository's practical AI R&D automation model is:

```text
Trellis planning
  -> Trellis implementation
  -> Trellis check
  -> durable knowledge ingest when useful
```

## Operating Model

- Trellis is the director for task lifecycle, planning, implementation, checking, and finish work.
- LLM-Wiki is the durable memory layer for reusable architecture, workflow, and domain knowledge.
- Trellis guides direct agents to load relevant wiki pages and cite evidence.
- Evaluation keeps the wiki and skills honest by comparing outputs on stable golden tasks.

## Workflow by Request Type

- Simple repository question: read the wiki index and relevant pages, answer with source paths, and avoid creating a Trellis task unless follow-up implementation is needed.
- Complex feature or refactor: use Trellis planning, consult relevant wiki pages, then implement through Trellis.
- Review: read the relevant task artifacts, wiki pages, and code paths before reporting findings.
- Troubleshooting: use `kb-problem-solve` to build an evidence chain before proposing fixes.
- New stable lesson: use `kb-ingest` to update `docs/llm-wiki/`.

## Known Limits

- The first iteration is Markdown-only and does not include vector search.
- The wiki is seeded from high-value architecture sources, not the full codebase.
- Current business domain remains partly template-like, especially around `Item`.

## Sources

- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]
- [[docs/llm-wiki/sources/backend-architecture|Backend architecture source]]
- [[docs/llm-wiki/sources/frontend-architecture|Frontend architecture source]]
- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]
- [[docs/llm-wiki/sources/private-knowledge-architecture|Private knowledge architecture source]]
