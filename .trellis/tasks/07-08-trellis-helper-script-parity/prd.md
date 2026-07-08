# Plan Trellis helper script parity

## Goal

Create an implementation plan for bringing useful Trellis helper scripts that exist in `.trellis-other` into this project's `.trellis` directory, without copying JSE_AI_Speckit project history, runtime state, or business-specific specs.

The target outcome is a reviewed migration plan that lets a later implementation safely adopt only the reusable Trellis plumbing.

## Background

`.trellis-other` is the `.trellis` directory from `D:\Workspace\JSE_AI_Speckit`. A comparison found that it contains helper scripts that are not present in the current project:

- `.trellis-other/scripts/spec_wiki.py`
- `.trellis-other/scripts/session_hook_runner.py`
- `.trellis-other/scripts/task_hook_runner.py`
- `.trellis-other/scripts/multi_agent/codex_handoff.py`
- `.trellis-other/scripts/multi_agent/worker.py`
- `.trellis-other/scripts/common/registry.py`
- `.trellis-other/scripts/common/worktree.py`
- `.trellis-other/tests/**`

The same comparison also found that both projects are Trellis `0.6.5`, `config.yaml` is identical, and the existing `agents/check.md` and `agents/implement.md` files match. The larger differences are project-specific specs, tasks, workspace journals, `.runtime`, and `.developer`, which must not be copied wholesale.

## Requirements

1. Produce a script-by-script inventory that classifies each missing helper as:
   - reusable as-is
   - reusable with adaptation
   - project-specific and not suitable for import
   - generated/cache and not suitable for tracking
2. Trace dependencies for each candidate script before copying anything, including imports from `scripts/common/**`, assumptions about Python command names, filesystem paths, runtime state, and platform hooks.
3. Keep the migration scope limited to reusable Trellis infrastructure. Do not import `.trellis-other/tasks/**`, `.trellis-other/workspace/**`, `.trellis-other/.runtime/**`, `.trellis-other/.developer`, or JSE/PMS/Tooling business specs.
4. Preserve this project's FastAPI/React Trellis spec content unless a helper script requires a small index/log file contract and the change is explicitly justified.
5. If `spec_wiki.py` is adopted, define how this project should maintain `.trellis/spec/index.md` and `.trellis/spec/log.md`.
6. If hook runners or multi-agent helpers are adopted, document how they connect to current Codex inline mode and avoid enabling sub-agent behavior accidentally.
7. Include validation commands for imported scripts and tests.

## Acceptance Criteria

- [ ] `design.md` explains which `.trellis-other` helper scripts are candidates, what each one does, and what must be adapted for this project.
- [ ] `implement.md` contains an ordered checklist for inventory, import, adaptation, validation, and rollback.
- [ ] The plan explicitly excludes project-specific history and runtime state from `.trellis-other`.
- [ ] The plan includes validation for `task.py`, `get_context.py`, any imported `spec_wiki.py` commands, and any imported tests.
- [ ] The task remains in `planning` until the user reviews the plan and asks to start implementation.

## Out Of Scope

- Bulk replacing this project's `.trellis` with `.trellis-other`.
- Importing JSE_AI_Speckit business specs, archived tasks, active tasks, workspace journals, runtime session markers, or developer identity.
- Changing application code outside Trellis infrastructure.
- Starting implementation before plan review.
