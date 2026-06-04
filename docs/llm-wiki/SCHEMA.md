---
title: LLM-Wiki Schema
created: 2026-06-04
updated: 2026-06-04
type: schema
tags:
  - llm-wiki
  - schema
status: active
---

# LLM-Wiki Schema

This file defines how agents maintain `docs/llm-wiki/`.

## Layer Mapping

- `L1 Sources`: code, architecture docs, Trellis tasks, specs, research notes, and existing internal knowledge docs.
- `L2 Wiki`: structured Markdown pages under `docs/llm-wiki/`.
- `L3 Schema`: this file, project skills under `.agents/skills/kb-*`, and Trellis workflow integration.

## Directory Contract

- `index.md`: content navigation, one-line summaries, and entrypoint for all wiki-aware work.
- `overview.md`: current state and operating model.
- `log.md`: append-only maintenance timeline.
- `sources/`: source summaries with traceable source paths.
- `concepts/`: reusable concepts, practices, and methods.
- `entities/`: systems, tools, modules, services, products, or repository entities.
- `syntheses/`: cross-source conclusions and workflow views.
- `queries/`: durable Q&A or investigations worth keeping.
- `evaluation/`: golden tasks and scoring rubrics for wiki/skill quality.

## Ingest

Use ingest when adding stable knowledge from a source.

1. Confirm the source path and whether it is authoritative.
2. Read the source, then extract topic, entities, key claims, constraints, and contradictions.
3. Create or update a page under `sources/`.
4. Update affected concept, entity, or synthesis pages when the source changes durable knowledge.
5. Update `index.md`.
6. Append a `## [YYYY-MM-DD] ingest | <title>` entry to `log.md`.

## Query

Use query when answering repository questions through the wiki.

1. Read `docs/llm-wiki/index.md` first.
2. Follow relevant wiki links before reading raw sources.
3. Distinguish wiki facts, source facts, code facts, and inference.
4. If the answer has durable value, create or update `queries/` or `syntheses/`.
5. Update `index.md` and `log.md` when new pages are created.

## Lint

Use lint to check wiki health.

- Every wiki page should have frontmatter: `title`, `created`, `updated`, `type`, `tags`, `status`.
- `index.md` should link every durable wiki page except README-like placeholders.
- Source pages should include source paths.
- Claims should be traceable to a source, code path, Trellis task, or explicit inference.
- Flag orphan pages, duplicate concepts, stale statements, missing cross-links, and completed Trellis tasks whose stable lessons were not ingested.

## Trellis Integration

- Trellis remains the task lifecycle and implementation workflow.
- LLM-Wiki stores cross-task durable knowledge.
- During Trellis spec update / finish work, decide whether task output should update `docs/llm-wiki/`.
- Do not replace `.trellis/tasks/**` with wiki pages. Task artifacts describe a work episode; wiki pages describe reusable knowledge.

