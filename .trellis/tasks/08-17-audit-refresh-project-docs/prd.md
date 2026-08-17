# Audit and refresh stale project documentation

## Goal

Make active project documentation match verified repository behavior without
rewriting historical records as current policy. This keeps maintenance guidance
actionable after the removal of CodeGraph requirements from Trellis specs and
after the Codex/Trellis dispatch behavior changed to default `auto`.

## Confirmed Facts

- Commit `a62f1d3` removed CodeGraph guidance from `.trellis/spec/**`, but
  active workflow docs still require or recommend CodeGraph-first retrieval.
- `.trellis/config.yaml` documents `auto` as the default
  `codex.dispatch_mode`; `.codex/hooks/inject-workflow-state.py` normalizes a
  missing value and the legacy `sub-agent` value to `auto`, while `inline` is
  an explicit opt-out and invalid explicit values fall back to `inline`.
- Active Codex guides, the Trellis/Codex hook document set, and related
  LLM-Wiki pages still describe `inline` as the default or describe an already
  implemented integration as future work.
- `docs/llm-wiki/overview.md` and `docs/llm-wiki/log.md` have stale
  maintenance metadata relative to their present contents.

## Requirements

1. Update active workflow, prompt, README, analysis, Codex, Trellis/Codex hook,
   and LLM-Wiki documents whose claims contradict those confirmed facts.
2. Replace CodeGraph-first wording with tool-neutral current-source inspection
   and narrow search guidance. Do not introduce a replacement tool mandate.
3. Document dispatch behavior consistently: `auto` is the default, `inline` is
   an opt-out, and `sub-agent` is a backwards-compatible alias for `auto`.
4. Convert `docs/specs/trellis-codex-hooks-subagents/` from an unfulfilled plan
   into a current-contract/historical-implementation record without erasing
   useful rationale or test intent.
5. Maintain LLM-Wiki traceability: update affected page frontmatter and append
   one maintenance record to `docs/llm-wiki/log.md`. Keep `index.md` unchanged
   unless navigation changes.
6. Preserve ADRs, GitHub/upstream summaries, archived task material, vendored
   `docs/skills/**`, and raw official-doc clippings as historical/reference
   material unless they make an active-current claim contradicted by source.
7. Do not change runtime configuration, hooks, application code, or
   `.trellis/spec/**` in this task.

## Acceptance Criteria

- [ ] Targeted active documentation contains no CodeGraph-first requirement or
  recommendation and does not name a new mandatory retrieval tool.
- [ ] Targeted Codex/Trellis documents agree with the source-of-truth dispatch
  semantics, including the missing-value and legacy-alias cases.
- [ ] The four `docs/specs/trellis-codex-hooks-subagents/*.md` files no longer
  present their completed integration as pending implementation.
- [ ] Edited LLM-Wiki pages have current `updated` frontmatter, their claims
  cite local sources, and `log.md` has one appended maintenance entry.
- [ ] Excluded historical and vendored material is unchanged.
- [ ] Focused stale-claim searches, Markdown link review, and `git diff --check`
  pass; no application test suite is required for this documentation-only task.

## Out of Scope

- Reintroducing or configuring CodeGraph.
- Changing Codex, Trellis, hook, dispatch, or model settings.
- Normalizing raw source clippings solely to add LLM-Wiki frontmatter.
- Broad prose rewrites unrelated to the verified stale claims.
