---
title: LLM-Wiki Log
created: 2026-06-04
updated: 2026-07-27
type: log
tags:
  - llm-wiki
status: active
---

# LLM-Wiki Log

Append new records at the end. Do not rewrite historical entries except for obvious typo fixes.

## [2026-06-04] bootstrap | Repository LLM-Wiki skeleton

- Created `docs/llm-wiki/` as the repository-level LLM-Wiki layer.
- Added schema, index, overview, source summaries, entity pages, concept pages, workflow synthesis, and initial evaluation artifacts.
- Added project skills under `.agents/skills/kb-*` for ingest, query, lint, technical solution, technical review, and problem solving.
- Integrated the wiki maintenance decision into the Trellis spec update phase.

## [2026-06-04] ingest | Architecture and workflow baseline

- Ingested source summaries for `ARCHITECTURE.md`, `backend/ARCHITECTURE.md`, `frontend/ARCHITECTURE.md`, `.trellis/workflow.md`, and `docs/私域知识工程体系产出/系统架构分析.md`.
- Created initial durable entities and concepts for the repository, Trellis, backend, frontend, spec-driven development, and LLM-Wiki R&D automation.
- Created [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]] as the cross-source operating model.

## [2026-06-04] maintenance | Usage guide

- Added [[docs/llm-wiki/usage-guide|usage guide]] to explain the new LLM-Wiki directories, seeded pages, project skills, common workflows, and maintenance rules.
- Updated [[docs/llm-wiki/index|index]] so users can discover the guide from the wiki entrypoint.

## [2026-06-07] ingest | Trellis Codex hooks and dispatch mode

- Added [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]] as a durable query page for Codex hook mapping, subagent lifecycle boundaries, and Trellis `codex.dispatch_mode` defaults.
- Updated [[docs/llm-wiki/index|index]] and [[docs/llm-wiki/entities/trellis|Trellis]] so future wiki-aware work can discover the Codex/Trellis integration decision.

## [2026-06-07] ingest | Codex official configuration docs

- Ingested local Codex documentation clippings under `docs/llm-wiki/sources/codex/` into [[docs/llm-wiki/sources/codex-official-configuration|Codex official configuration source]].
- Added [[docs/llm-wiki/entities/codex|Codex]] as the durable entity page for repository-relevant Codex surfaces: config, hooks, subagents, rules, skills, and plugins.
- Updated [[docs/llm-wiki/index|index]] and [[docs/llm-wiki/entities/trellis|Trellis]] so future wiki-aware work can discover Codex integration guidance.

## [2026-07-27] ingest | Scheduler runtime boundary

- Added [[docs/llm-wiki/sources/scheduler-runtime|Scheduler runtime source]]
  from the scheduler code-spec, reviewed Trellis task, migration, and runtime
  implementation.
- Recorded the durable PostgreSQL/Celery dispatch lease, credential boundary,
  startup validation, failure classification, concurrency, and Shanghai-time
  input contracts.
- Updated [[docs/llm-wiki/index|index]] so scheduler runtime guidance is
  discoverable during future backend and frontend work.

## [2026-07-31] ingest | Scheduler alert delivery boundary

- Corrected [[docs/llm-wiki/sources/scheduler-runtime|Scheduler runtime source]]
  from the archived scheduler task, current async-task code-spec, and runtime
  code: SMTP or alert-recipient configuration no longer blocks Celery startup.
- Recorded that scheduler alerts persist per-recipient outbox rows; empty
  recipients log `scheduler.alert.unsent`, and SMTP delivery/retry belongs to
  the generic outbox boundary.

## [2026-08-01] ingest | Scheduler manual-backfill capability boundary

- Updated [[docs/llm-wiki/sources/scheduler-runtime|Scheduler runtime source]]
  from the completed D-003 task and current scheduler implementation.
- Recorded that `allow_backfill` is default-deny static implementation metadata,
  both current inventory tasks remain non-replayable, and only a future class
  with explicit replay-safe historical semantics may opt into the completed
  365-day single-point backfill window.

## [2026-08-02] maintenance | Simplify LLM-Wiki skills

- Removed `kb-query`, `kb-tech-solution`, and `kb-tech-review`; their generic
  wiki-loading guidance is covered by Trellis guides and review workflow.
- Kept `kb-ingest`, `kb-lint`, and `kb-problem-solve` for wiki maintenance and
  evidence-first troubleshooting.
- Updated the usage guide and repository AI R&D workflow to remove obsolete
  skill references.
