---
title: LLM-Wiki Overview
created: 2026-06-04
updated: 2026-08-17
type: overview
tags:
  - llm-wiki
  - ai-engineering
status: active
---

# LLM-Wiki Overview

`docs/llm-wiki/` is the repository's durable knowledge layer for AI-assisted engineering.

It complements Trellis:

- Trellis manages task lifecycle, planning artifacts, implementation context, checks, commits, and finish work.
- LLM-Wiki keeps reusable knowledge that should survive across tasks.
- Skills under `.agents/skills/kb-*` route agents through the wiki before producing plans, reviews, troubleshooting output, or new knowledge pages.

## Current Scope

The current scope covers repository architecture, AI workflow, and selected
operational integrations:

- top-level architecture
- backend architecture
- frontend architecture
- Trellis workflow
- existing Chinese private-knowledge architecture summary
- scheduler runtime and alert/backfill boundaries
- Codex configuration, hooks, and Trellis dispatch-mode integration

It does not ingest the full codebase, create a vector index, or connect external MCP services.

## Operating Model

- Use `index.md` as the first read.
- Use `SCHEMA.md` for maintenance rules.
- Keep source pages traceable to source paths.
- Update `log.md` whenever durable pages change through ingest, query, lint, or maintenance.
- Prefer small, reviewed wiki updates over broad automatic rewrites.

## Relationship to Existing Docs

Existing docs remain authoritative in their own scope:

- `ARCHITECTURE.md`
- `backend/ARCHITECTURE.md`
- `frontend/ARCHITECTURE.md`
- `.trellis/workflow.md`
- `docs/私域知识/**`
- `docs/私域知识工程体系产出/**`

The wiki summarizes and links those sources. It does not replace or migrate them.
