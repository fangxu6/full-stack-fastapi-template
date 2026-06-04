---
title: Trellis
created: 2026-06-04
updated: 2026-06-04
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

## Sources

- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]
- [[docs/llm-wiki/concepts/spec-driven-development|Spec-driven development]]

