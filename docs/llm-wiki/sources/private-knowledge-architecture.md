---
title: Private knowledge architecture source
created: 2026-06-04
updated: 2026-06-04
type: source
tags:
  - llm-wiki
  - private-knowledge
  - architecture
status: active
source_count: 1
---

# Private Knowledge Architecture Source

## Source

- Path: `docs/私域知识工程体系产出/系统架构分析.md`
- Role: Chinese internal architecture analysis and current private-knowledge maintenance guidance.

## Key Facts

- The documented business domain is an account, docs, and item management platform.
- The architecture summary confirms FastAPI, React, PostgreSQL, Docker Compose, and Traefik.
- Batch-0 platformization is already reflected: backend unified exceptions/request tracing and frontend `app/platform/features/shared` boundaries.
- Authentication and permission flows are clear, while `Item` remains template-like and `modules/*` / `infra/*` remain mostly skeletons.
- The document contains maintenance rules for updating architecture diagrams and knowledge summaries when backend or frontend boundaries change.

## Durable Guidance

- Preserve existing `docs/私域知识/**` and `docs/私域知识工程体系产出/**` as source material.
- Use LLM-Wiki as a stricter, traceable AI-maintained layer, not as a replacement for existing Chinese knowledge docs.
- Update relevant source docs when actual architecture changes, then ingest durable conclusions into the wiki.

## Related Pages

- [[docs/llm-wiki/entities/full-stack-fastapi-template|full-stack-fastapi-template]]
- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]

