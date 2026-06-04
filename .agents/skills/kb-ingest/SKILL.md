---
name: kb-ingest
description: Ingest durable repository knowledge into docs/llm-wiki from architecture docs, code findings, Trellis tasks, research notes, external articles, or completed work. Use when adding or updating LLM-Wiki source summaries, concepts, entities, syntheses, query records, index entries, or log records.
---

# KB Ingest

Turn a source into durable wiki knowledge under `docs/llm-wiki/`.

## Required Reads

1. Read `docs/llm-wiki/SCHEMA.md`.
2. Read `docs/llm-wiki/index.md`.
3. Read the source being ingested.
4. Read affected existing wiki pages before editing them.

## Workflow

1. Confirm the source path and source type: docs, code, Trellis task, research, external source, or query result.
2. Extract topic, key entities, durable claims, constraints, risks, contradictions, and open questions.
3. Create or update a page under the right wiki directory:
   - `sources/` for source summaries.
   - `concepts/` for reusable ideas or methods.
   - `entities/` for systems, tools, modules, or products.
   - `syntheses/` for cross-source conclusions.
   - `queries/` for durable Q&A or investigations.
4. Keep every factual claim traceable to a source path, code path, Trellis task path, or explicit inference.
5. Update `docs/llm-wiki/index.md`.
6. Append to `docs/llm-wiki/log.md`.

## Rules

- Do not rewrite source-of-truth files unless the user explicitly asked for source maintenance.
- Prefer updating an existing concept/entity over creating a duplicate.
- Use frontmatter on every new wiki page: `title`, `created`, `updated`, `type`, `tags`, `status`.
- Mark inference as inference.
- Keep index entries short.

