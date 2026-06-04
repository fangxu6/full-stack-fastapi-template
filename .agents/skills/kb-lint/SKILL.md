---
name: kb-lint
description: Check docs/llm-wiki health: index coverage, frontmatter, missing source paths, orphan pages, duplicate concepts, stale claims, broken wikilinks, and Trellis task lessons that should be ingested. Use when asked to lint, audit, maintain, or improve the repository LLM-Wiki.
---

# KB Lint

Audit `docs/llm-wiki/` for maintainability and traceability.

## Required Reads

1. Read `docs/llm-wiki/SCHEMA.md`.
2. Read `docs/llm-wiki/index.md`.
3. List all files under `docs/llm-wiki/`.
4. Read pages relevant to any detected issue.

## Checks

- Every durable page has frontmatter with `title`, `created`, `updated`, `type`, `tags`, `status`.
- `index.md` links durable pages.
- `log.md` contains records for recent ingest/query/lint/maintenance work.
- Source pages include source paths.
- Wikilinks point to existing pages or clearly intentional future pages.
- Concepts are not duplicated under different names.
- Claims that look stale are flagged with source paths and verification steps.
- Completed Trellis tasks with reusable lessons are considered for ingest.

## Output

Group findings by severity:

- High: broken entrypoint, misleading stale claim, missing source traceability for important facts.
- Medium: missing index entry, orphan page, duplicate concept, incomplete frontmatter.
- Low: naming cleanup, weak cross-linking, minor wording issue.

If fixes are requested, apply them through `kb-ingest` rules and update `log.md`.

