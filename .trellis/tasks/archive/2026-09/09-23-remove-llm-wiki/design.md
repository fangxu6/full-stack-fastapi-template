# Technical Design

## Boundary

This is a repository documentation and agent-skill removal. There is no runtime, API, database, or generated-client behavior to change.

## Changes

- Remove all files under `docs/llm-wiki/`.
- Remove all files under the three dedicated `.agents/skills/kb-*` directories.
- Update active guidance in `.trellis/spec/guides/index.md`, `docs/rules/**`, `docs/specs/trellis-codex-hooks-subagents/**`, `docs/trellis-spec-diff-analysis.md`, and the Trellis knowledge-settlement guide.
- Replace durable-knowledge routing with the remaining `.trellis/spec/**`, `docs/specs/**`, and human-maintained documentation paths where the surrounding text requires a destination.
- Remove dead reference-only bullets and acceptance clauses where no replacement is needed.

## Compatibility and Scope

- Preserve `.trellis/tasks/archive/**` exactly; archive references describe historical state, not active capability.
- Preserve `.trellis/scripts/spec_wiki.py` and its `.trellis/spec/**` contract; its name and purpose are separate from LLM-Wiki. The shared guide index may receive reference-only cleanup.
- Do not delete general private-knowledge documentation or unrelated skills.
- Do not modify the two pre-existing user-owned deletions.

## Verification

Use path-scoped searches to prove no active guidance references the removed capability, then run Markdown whitespace validation and the independent Trellis spec lint.
