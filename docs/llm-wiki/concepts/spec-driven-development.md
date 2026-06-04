---
title: Spec-driven development
created: 2026-06-04
updated: 2026-06-04
type: concept
tags:
  - llm-wiki
  - spec
  - trellis
status: active
---

# Spec-Driven Development

## Summary

Spec-driven development in this repository means work is planned and persisted before implementation. Requirements, design, execution steps, research, and checks live in files rather than transient chat context.

## Repository Implementation

- Trellis tasks hold `prd.md`, optional `design.md`, optional `implement.md`, research files, and context manifests.
- `.trellis/spec/**` holds coding and architectural guidelines by package/layer.
- Implementation and check phases load task artifacts and relevant specs before editing or reviewing code.
- The finish phase reviews whether specs need updates after learning something new.

## LLM-Wiki Connection

Trellis specs guide a single task. LLM-Wiki stores reusable knowledge across tasks. When repeated lessons, architecture constraints, or decision patterns appear, they should be ingested into durable wiki pages.

## Sources

- [[docs/llm-wiki/sources/trellis-workflow|Trellis workflow source]]
- [[docs/llm-wiki/syntheses/repo-ai-rd-workflow|Repository AI R&D workflow]]

