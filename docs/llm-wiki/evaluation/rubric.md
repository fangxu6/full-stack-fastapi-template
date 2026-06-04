---
title: LLM-Wiki Evaluation Rubric
created: 2026-06-04
updated: 2026-06-04
type: evaluation
tags:
  - llm-wiki
  - evaluation
status: active
---

# LLM-Wiki Evaluation Rubric

Score each task out of 100.

## Evidence Accuracy: 25

- Uses real source paths, code paths, Trellis artifacts, or wiki pages.
- Separates source facts from inference.
- Avoids citing pages that do not support the claim.

## Architecture Consistency: 20

- Follows backend and frontend target boundaries.
- Preserves Trellis as task lifecycle and LLM-Wiki as durable knowledge.
- Does not reintroduce old flat template patterns.

## Task Completion: 20

- Answers the actual user request.
- Provides implementation-ready guidance when asked for a plan.
- Identifies missing information only when it materially changes the outcome.

## Anti-Hallucination: 20

- Does not invent files, APIs, tables, modules, commands, or behavior.
- Marks uncertainty and verification needs clearly.
- Does not overstate conclusions from limited evidence.

## Test and Review Quality: 15

- Suggests checks proportional to risk.
- Covers cross-layer consistency when backend and frontend both change.
- Includes documentation/wiki maintenance when durable knowledge changes.

