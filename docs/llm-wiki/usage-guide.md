---
title: LLM-Wiki Usage Guide
created: 2026-06-04
updated: 2026-06-04
type: guide
tags:
  - llm-wiki
  - guide
status: active
---

# LLM-Wiki Usage Guide

This guide explains the new LLM-Wiki directories and project skills added for AI-assisted development.

## What This Is

`docs/llm-wiki/` is the durable knowledge layer for this repository.

Use it when you need an agent to understand the project before answering, designing, reviewing, troubleshooting, or maintaining documentation.

It does not replace:

- `.trellis/`: task lifecycle, PRD/design/implementation artifacts, implementation and check workflow.
- `ARCHITECTURE.md`, `backend/ARCHITECTURE.md`, `frontend/ARCHITECTURE.md`: source architecture docs.
- `docs/私域知识/**` and `docs/私域知识工程体系产出/**`: existing Chinese knowledge documents.

## Directory Map

| Path | Purpose |
| --- | --- |
| `docs/llm-wiki/index.md` | Main navigation entry. Start here for wiki-aware work. |
| `docs/llm-wiki/SCHEMA.md` | Maintenance rules for ingest, query, lint, and Trellis integration. |
| `docs/llm-wiki/overview.md` | Current state and operating model of the repository wiki. |
| `docs/llm-wiki/log.md` | Append-only maintenance timeline. |
| `docs/llm-wiki/sources/` | Source summaries with traceable source paths. |
| `docs/llm-wiki/entities/` | Repository entities such as backend, frontend, Trellis, and the repo itself. |
| `docs/llm-wiki/concepts/` | Reusable concepts such as spec-driven development and LLM-Wiki automation. |
| `docs/llm-wiki/syntheses/` | Cross-source conclusions and workflow summaries. |
| `docs/llm-wiki/queries/` | Durable Q&A or investigation notes. Empty until useful questions are saved. |
| `docs/llm-wiki/evaluation/` | Golden tasks and scoring rubric for evaluating wiki/skill quality. |

## Seeded Wiki Pages

### Core Entry Files

- [[docs/llm-wiki/index|index]]: Wiki entrypoint and page directory.
- [[docs/llm-wiki/SCHEMA|SCHEMA]]: Rules for agents maintaining the wiki.
- [[docs/llm-wiki/overview|overview]]: Current wiki scope and relationship with Trellis.
- [[docs/llm-wiki/log|log]]: Maintenance history.

### Source Summaries

- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]: Summary of `ARCHITECTURE.md`.
- [[docs/llm-wiki/sources/backend-architecture|Backend architecture source]]: Summary of `backend/ARCHITECTURE.md`.
- [[docs/llm-wiki/sources/frontend-architecture|Frontend architecture source]]: Summary of `frontend/ARCHITECTURE.md`.
- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]: Summary of `.trellis/workflow.md`.
- [[docs/llm-wiki/sources/private-knowledge-architecture|Private knowledge architecture source]]: Summary of `docs/私域知识工程体系产出/系统架构分析.md`.

### Entities

- [[docs/llm-wiki/entities/full-stack-fastapi-template|full-stack-fastapi-template]]: Repository-level entity summary.
- [[docs/llm-wiki/entities/trellis|Trellis]]: Task workflow and spec-memory system.
- [[docs/llm-wiki/entities/fastapi-backend|FastAPI backend]]: Backend boundaries and durable rules.
- [[docs/llm-wiki/entities/react-frontend|React frontend]]: Frontend boundaries and durable rules.

### Concepts and Synthesis

- [[docs/llm-wiki/concepts/spec-driven-development|Spec-driven development]]: How Trellis artifacts guide implementation.
- [[docs/llm-wiki/concepts/llm-wiki-for-rd-automation|LLM-Wiki for R&D automation]]: How wiki knowledge supports AI engineering workflows.
- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]: Practical workflow combining Trellis, wiki, skills, and evaluation.

### Evaluation

- [[docs/llm-wiki/evaluation/golden-tasks|Golden tasks]]: Initial task set for evaluation.
- [[docs/llm-wiki/evaluation/rubric|Rubric]]: Scoring criteria for wiki-assisted output quality.

## Project Skills

The new skills live under `.agents/skills/`.

| Skill | Use When |
| --- | --- |
| `kb-query` | Answering repository-aware questions through the wiki. |
| `kb-ingest` | Adding durable knowledge from docs, code findings, Trellis tasks, research, or completed work. |
| `kb-lint` | Auditing wiki health, links, frontmatter, index coverage, and source traceability. |
| `kb-tech-solution` | Producing source-backed technical solutions or implementation plans. |
| `kb-tech-review` | Reviewing specs, plans, or code changes against wiki, architecture, Trellis, and code evidence. |
| `kb-problem-solve` | Troubleshooting by building an evidence chain before proposing fixes. |

## Common Workflows

### Ask a Repository Question

Use `kb-query`.

Expected flow:

1. Read `docs/llm-wiki/index.md`.
2. Read relevant wiki pages.
3. Verify source docs or code only when needed.
4. Answer with evidence paths and clear assumptions.

Example prompt:

```text
Use kb-query: 当前仓库前后端边界是什么？
```

### Add New Knowledge

Use `kb-ingest`.

Expected flow:

1. Read `docs/llm-wiki/SCHEMA.md`.
2. Read the source.
3. Add or update the right wiki page.
4. Update `index.md`.
5. Append to `log.md`.

Example prompt:

```text
Use kb-ingest: 将 .trellis/tasks/<task>/research 下的稳定结论沉淀进 docs/llm-wiki。
```

### Create a Technical Solution

Use `kb-tech-solution`.

Expected flow:

1. Read wiki index and relevant pages.
2. Read Trellis task artifacts if present.
3. Verify affected source docs or code.
4. Produce a plan that follows backend/frontend/Trellis boundaries.
5. Identify whether `.trellis/spec/**` or `docs/llm-wiki/**` needs updates.

Example prompt:

```text
Use kb-tech-solution: 为新增一个需要前后端联动的管理页提供方案。
```

### Review a Plan or Change

Use `kb-tech-review`.

Expected output should separate:

- Confirmed issue
- Risk inference
- Needs human confirmation

Example prompt:

```text
Use kb-tech-review: 审查这个 design.md 是否违反仓库架构边界。
```

### Troubleshoot a Problem

Use `kb-problem-solve`.

Expected flow:

1. Capture symptom exactly.
2. Map expected flow from wiki and source docs.
3. Read relevant code/tests/logs.
4. Form and verify hypotheses.
5. Propose fix and validation steps.
6. Decide whether the lesson should update wiki or Trellis specs.

Example prompt:

```text
Use kb-problem-solve: 登录接口返回 500，响应里有 request_id，帮我定位排查路径。
```

### Maintain Wiki Health

Use `kb-lint`.

Expected checks:

- Missing frontmatter
- Broken wikilinks
- Missing index entries
- Source pages without source paths
- Duplicate concepts
- Stale claims
- Completed Trellis tasks that should be ingested

Example prompt:

```text
Use kb-lint: 检查 docs/llm-wiki 是否有断链、孤页或缺少来源的问题。
```

## Trellis Integration

Trellis remains the main task workflow.

During `.trellis/workflow.md` Phase 3.3 spec update, agents now also decide whether the task produced durable knowledge for `docs/llm-wiki/`.

Use this rule:

- Update `.trellis/spec/**` when the lesson is a coding guideline, convention, or prevention rule.
- Update `docs/llm-wiki/**` when the lesson is reusable architecture, domain, workflow, troubleshooting, or cross-task knowledge.
- Update both when a new convention also changes durable project understanding.
- Update neither when the finding is task-local and unlikely to help future work.

## Maintenance Rules

- Do not bulk-ingest the whole repository without a reviewed plan.
- Do not rewrite source-of-truth docs just to make a wiki page cleaner.
- Keep source summaries traceable to source paths.
- Keep `index.md` short and navigable.
- Append `log.md`; do not rewrite history.
- Mark inference explicitly when a conclusion is not directly sourced.

