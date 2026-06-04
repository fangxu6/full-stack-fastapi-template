---
name: kb-problem-solve
description: Troubleshoot repository issues by building an evidence chain through docs/llm-wiki, architecture docs, logs/errors, code paths, Trellis tasks, and tests. Use for debugging, incident analysis, root-cause investigation, or "why is this failing" questions.
---

# KB Problem Solve

Troubleshoot with evidence before proposing fixes.

## Required Reads

1. Read `docs/llm-wiki/index.md`.
2. Read relevant wiki pages for architecture and known flows.
3. Read the reported error, logs, failing test, or reproduction steps.
4. Read affected source code and tests before naming a root cause.

## Workflow

1. Capture the symptom exactly: error message, request ID, route, command, test, or UI behavior.
2. Map the likely flow using wiki pages and source docs.
3. Build evidence:
   - observed failure
   - expected behavior
   - relevant code paths
   - recent task/spec changes when available
4. Form hypotheses and mark confidence.
5. Verify the strongest hypothesis with code, tests, logs, or minimal reproduction.
6. Propose fix options with validation steps.
7. Identify whether the lesson should update `docs/llm-wiki/` or `.trellis/spec/**`.

## Rules

- Do not patch before establishing a credible root cause.
- Distinguish root cause, contributing factor, and unrelated observation.
- For backend errors, preserve request ID and shared error-contract expectations.
- For frontend issues, check route/page/layer boundaries and generated-client usage.

