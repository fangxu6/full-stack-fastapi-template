---
name: kb-tech-review
description: Review technical plans, specs, or code changes against docs/llm-wiki, repository architecture, Trellis artifacts, and real code evidence. Use for design review, implementation review, spec compliance review, and anti-hallucination checks.
---

# KB Tech Review

Review plans or changes against durable repository knowledge and source evidence.

## Required Reads

1. Read `docs/llm-wiki/index.md`.
2. Read relevant wiki pages and source summaries.
3. Read the reviewed artifact: PRD, design, implementation plan, diff, or code.
4. Read real code/source paths before claiming a concrete mismatch.

## Review Dimensions

- Requirement alignment: does the plan satisfy the stated goal?
- Architecture boundary: does it follow backend/frontend/Trellis/wiki responsibilities?
- Evidence accuracy: are file paths, APIs, schemas, and behaviors real?
- Cross-layer consistency: do backend, OpenAPI client, frontend, and docs agree?
- Risk handling: auth, validation, errors, rollback, migrations, and tests.
- Knowledge maintenance: should `.trellis/spec/**` or `docs/llm-wiki/**` be updated?

## Finding Classes

- Confirmed issue: backed by specific source or code evidence.
- Risk inference: plausible risk, but not yet proven by source.
- Needs human confirmation: product, policy, or business decision not derivable from repository evidence.

## Output Rules

- Findings first, ordered by severity.
- Include file paths or wiki/source pages for evidence.
- Do not overstate risk in the absence of evidence.
- Avoid accepting a plan just because it cites wiki pages; verify the cited pages support the claim.

