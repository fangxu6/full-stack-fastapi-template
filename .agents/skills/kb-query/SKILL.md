---
name: kb-query
description: Answer repository-aware questions using docs/llm-wiki first, then source docs, code, or Trellis artifacts as needed. Use for architecture questions, workflow questions, domain knowledge lookup, "where should this go", and other queries that benefit from durable project knowledge.
---

# KB Query

Answer through the LLM-Wiki knowledge graph before falling back to raw sources.

## Required Reads

1. Read `docs/llm-wiki/index.md`.
2. Read all relevant wiki pages linked from the index.
3. Read raw source docs, code, or Trellis artifacts only when the wiki is insufficient or verification is needed.

## Workflow

1. Classify the question: architecture, workflow, implementation placement, review, troubleshooting, or documentation maintenance.
2. Follow index links to relevant sources, entities, concepts, or syntheses.
3. Verify high-risk claims against source paths or code.
4. Answer with clear evidence:
   - wiki facts
   - source facts
   - code facts
   - inference
5. If the answer has durable value, suggest or perform a `kb-ingest` update when appropriate.

## Output Rules

- Cite file paths or wiki pages for concrete claims.
- Say when the wiki lacks coverage.
- Do not invent files, APIs, modules, or rules.
- Keep simple answers concise; use structure for cross-layer guidance.

