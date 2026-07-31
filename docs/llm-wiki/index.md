---
title: LLM-Wiki Index
created: 2026-06-04
updated: 2026-07-31
type: index
tags:
  - llm-wiki
status: active
---

# LLM-Wiki Index

This is the entrypoint for repository-aware AI work. Read this file before answering questions, creating designs, reviewing plans, or maintaining wiki pages.

## Overview

- [[docs/llm-wiki/overview|overview]]: Current state of the repository LLM-Wiki and its role beside Trellis.
- [[docs/llm-wiki/SCHEMA|SCHEMA]]: Maintenance rules for ingest, query, lint, and Trellis integration.
- [[docs/llm-wiki/usage-guide|usage guide]]: Directory/file explanation and practical usage guide for repository users.

## Sources

- [[docs/llm-wiki/sources/root-architecture|Root architecture source]]: Top-level repository architecture, stack, boundaries, and integration flows.
- [[docs/llm-wiki/sources/backend-architecture|Backend architecture source]]: FastAPI backend structure, request flow, error handling, and module-growth guidance.
- [[docs/llm-wiki/sources/scheduler-runtime|Scheduler runtime source]]: Durable PostgreSQL/Celery scheduler dispatch, configuration, and failure-boundary rules.
- [[docs/llm-wiki/sources/frontend-architecture|Frontend architecture source]]: React frontend layering, route boundaries, navigation, and shared component strategy.
- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]: Task lifecycle, planning artifacts, implementation/check phases, and finish workflow.
- [[docs/llm-wiki/sources/private-knowledge-architecture|Private knowledge architecture source]]: Chinese internal architecture analysis and existing knowledge-maintenance rules.
- [[docs/llm-wiki/sources/codex-official-configuration|Codex official configuration source]]: Local OpenAI Codex documentation summary for config, hooks, subagents, and command rules.

## Entities

- [[docs/llm-wiki/entities/full-stack-fastapi-template|full-stack-fastapi-template]]: Repository entity and current system boundary summary.
- [[docs/llm-wiki/entities/trellis|Trellis]]: Task workflow and spec-memory system used by this repository.
- [[docs/llm-wiki/entities/codex|Codex]]: Coding-agent runtime and project customization surfaces for config, hooks, subagents, rules, skills, and plugins.
- [[docs/llm-wiki/entities/fastapi-backend|FastAPI backend]]: Backend application boundary and platform baseline.
- [[docs/llm-wiki/entities/react-frontend|React frontend]]: Frontend application boundary and platform/feature/shared layering.

## Concepts

- [[docs/llm-wiki/concepts/spec-driven-development|Spec-driven development]]: How specs, tasks, research, implementation, and check artifacts guide work.
- [[docs/llm-wiki/concepts/llm-wiki-for-rd-automation|LLM-Wiki for R&D automation]]: How write-time knowledge compilation supports AI-assisted engineering.

## Syntheses

- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]: How Trellis, LLM-Wiki, skills, and evaluation combine into a practical automation loop.

## Queries

- [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]]: Codex hook mapping, `SubagentStart`/`SubagentStop` responsibilities, and Trellis `codex.dispatch_mode` defaults.

## Evaluation

- [[docs/llm-wiki/evaluation/golden-tasks|Golden tasks]]: Initial task set for comparing wiki-assisted and baseline answers.
- [[docs/llm-wiki/evaluation/rubric|Rubric]]: Scoring dimensions for wiki and skill effectiveness.

## Maintenance

- [[docs/llm-wiki/log|log]]: Append-only maintenance timeline.
