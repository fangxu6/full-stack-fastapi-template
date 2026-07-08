# Design: Trellis helper script parity

## Boundary

This task is about Trellis infrastructure under `.trellis/**` only. The reference source is `.trellis-other/**`, but `.trellis-other` belongs to a different project and must be treated as evidence, not as a drop-in replacement.

Allowed candidate areas:

- `.trellis/scripts/spec_wiki.py`
- `.trellis/scripts/session_hook_runner.py`
- `.trellis/scripts/task_hook_runner.py`
- `.trellis/scripts/multi_agent/**`
- `.trellis/scripts/common/registry.py`
- `.trellis/scripts/common/worktree.py`
- selected `.trellis/tests/**` that exercise reusable Trellis behavior
- small workflow/spec catalog references only when required by adopted scripts

Explicitly excluded areas:

- `.trellis-other/tasks/**`
- `.trellis-other/workspace/**`
- `.trellis-other/.runtime/**`
- `.trellis-other/.developer`
- `.trellis-other/spec/**` business contracts for JSE/PMS/Tooling/Training
- Python bytecode caches and update markers

## Candidate Script Notes

| Candidate | Expected role | Initial import decision |
| --- | --- | --- |
| `spec_wiki.py` | Builds and lints a global Trellis spec catalog plus append-only maintenance log. | Candidate, but must be adapted to current FastAPI/React spec shape. |
| `session_hook_runner.py` | Runs session lifecycle hooks through common hook plumbing. | Candidate, only if current platform hooks need this indirection. |
| `task_hook_runner.py` | Runs task lifecycle hooks through common hook plumbing. | Candidate, only with dependency review against `common/hooks.py` and config handling. |
| `multi_agent/codex_handoff.py` | Supports Codex handoff/context behavior for multi-agent workflows. | Caution: current project is in Codex inline mode; do not enable sub-agent routing accidentally. |
| `multi_agent/worker.py` | Supports Trellis worker execution. | Caution: import only if tests and workflow actually need it. |
| `common/registry.py` | Shared registry helper used by hook or multi-agent plumbing. | Candidate if imported by selected scripts. |
| `common/worktree.py` | Shared worktree helper for worker or handoff flows. | Candidate if imported by selected scripts. |
| `tests/**` | Regression tests for Trellis hooks/workflow/subagent behavior. | Candidate subset; remove cache files and adapt project-specific assertions. |

## Compatibility Rules

- Keep the current project's command style unless the runtime requires otherwise. `.trellis-other` mostly changed help text from `python` to `python3`, which is not automatically appropriate on this Windows PowerShell checkout.
- Preserve Codex inline dispatch mode. Imported multi-agent helpers must not change the active workflow from inline to sub-agent.
- If `spec_wiki.py` is adopted, generate a catalog from the current project's actual `.trellis/spec/**` files, not from `.trellis-other/spec/**`.
- Do not copy `.template-hashes.json` wholesale. If generated-file hashes need updates, regenerate or update only after the selected files are imported.

## Data Flow

1. Inventory `.trellis-other` candidate scripts and their imports.
2. Map each import to an existing current-project file or an additional candidate.
3. Decide whether each candidate is infrastructure, project-specific policy, or generated state.
4. Copy only approved infrastructure files.
5. Adapt command text, workflow references, and tests to current project conventions.
6. Validate scripts and tests before any task activation or commit.

## Rollback

All changes should be limited to the new task directory plus selected `.trellis/scripts/**`, `.trellis/tests/**`, and narrowly justified `.trellis/workflow.md` or `.trellis/spec/index.md` files. Rollback is deleting the imported candidate files and reverting any workflow/spec catalog edits from the same change set.
