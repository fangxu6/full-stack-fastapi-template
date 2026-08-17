# Design: Documentation freshness audit

## Source of Truth

| Subject | Authoritative evidence | Documentation action |
| --- | --- | --- |
| CodeGraph policy | `a62f1d3` and current `.trellis/spec/**` | Remove active CodeGraph-first directives; retain tool-neutral source inspection. |
| Codex dispatch | `.trellis/config.yaml` and `_resolve_codex_dispatch_mode()` | State `auto` default, `inline` opt-out, and `sub-agent` legacy alias. |
| Native context injection | `.codex/hooks.json` and hook scripts | Describe the registered `SubagentStart` contract as implemented, not planned. |
| LLM-Wiki maintenance | `docs/llm-wiki/SCHEMA.md` and existing index | Update existing pages and append the log; do not add duplicate pages. |

## Boundaries

The edit is limited to active policy, instructional, planning-status, and
durable knowledge pages. Historical decisions, upstream reports, archived task
artifacts, vendored skills, and raw source snapshots retain their original
wording unless they assert a current policy contradicted by the authoritative
source.

The `docs/specs/trellis-codex-hooks-subagents/` documents stay in place so
their rationale and validation history remain discoverable. Their language is
changed only enough to distinguish completed work from current configuration.

## Compatibility and Rollback

No runtime behavior changes. Rollback is a normal Git revert of this
documentation-only commit. The documentation must not prescribe a config edit
or a different execution mode.
