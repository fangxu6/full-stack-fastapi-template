---
title: Trellis
created: 2026-06-04
updated: 2026-06-07
type: entity
tags:
  - llm-wiki
  - trellis
  - workflow
status: active
---

# Trellis

## Summary

Trellis is the repository's task lifecycle, spec-memory, and AI workflow system. It owns planning, task artifacts, context routing, implementation/check phases, spec updates, and finish-work bookkeeping.

## Responsibilities

- Create and track work under `.trellis/tasks/**`.
- Persist requirements in `prd.md`.
- Persist complex technical design in `design.md`.
- Persist execution order and validation in `implement.md`.
- Route agents through `.trellis/spec/**` and task research.
- Require final verification, spec update review, and commit planning.

## LLM-Wiki Relationship

Trellis task artifacts are episodic. LLM-Wiki pages are durable. When a task produces stable architecture, domain, debugging, or workflow knowledge, ingest the reusable conclusion into `docs/llm-wiki/`.

For Codex-specific workflow behavior, keep durable hook and dispatch-mode decisions in query pages so local Trellis workflow files can stay focused on execution.

## Sources

- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]
- [[docs/llm-wiki/entities/codex|Codex]]
- [[docs/llm-wiki/concepts/spec-driven-development|Spec-driven development]]
- [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]]
