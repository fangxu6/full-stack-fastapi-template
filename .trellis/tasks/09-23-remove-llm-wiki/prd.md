# Remove LLM-Wiki and knowledge-base skills

## Goal

Remove docs/llm-wiki, the three kb-* skills, and current documentation references while preserving archived history and Trellis spec tooling.

## Confirmed Facts

- `docs/llm-wiki/` contains the repository's durable LLM-Wiki content.
- `.agents/skills/kb-ingest/`, `.agents/skills/kb-lint/`, and `.agents/skills/kb-problem-solve/` are dedicated to that wiki.
- Current rules, specs, tutorials, and the shared Trellis guide index still reference the removed capability.
- `.trellis/scripts/spec_wiki.py` manages `.trellis/spec/**` and is independent of `docs/llm-wiki/`.
- The worktree already contains user-owned deletions of `docs/postgresql-export.md` and `docs/upstream-master-merge-2026-07-08.md`; they are outside this task.

## Requirements

1. Delete the complete `docs/llm-wiki/` tree.
2. Delete the three dedicated `kb-*` skill directories.
3. Remove or rewrite current references so active guidance does not point to the deleted wiki or skills.
4. Keep archived Trellis task records unchanged for historical traceability.
5. Keep `.trellis/spec/**` behavior and `.trellis/scripts/spec_wiki.py` unchanged; update only the shared guide index's dead LLM-Wiki references.

## Acceptance Criteria

- [x] The four target trees are absent from the resulting worktree.
- [x] Active files outside `.trellis/tasks/**` contain no references to `llm-wiki`, `LLM-Wiki`, `kb-ingest`, `kb-lint`, or `kb-problem-solve`.
- [x] Archived task records remain unchanged and may retain historical references.
- [x] `python3 ./.trellis/scripts/spec_wiki.py lint` passes.
- [x] `git diff --check` passes.
- [x] Existing user-owned deletions remain untouched.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
