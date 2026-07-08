# Implementation Plan: Trellis helper script parity

## Checklist

1. Re-run a focused inventory:
   - List files present in `.trellis-other/scripts/**` but missing in `.trellis/scripts/**`.
   - Exclude `__pycache__`, `.runtime`, `workspace`, `tasks`, `.developer`, and business specs.
2. Trace dependencies:
   - For each candidate script, inspect imports and file/path assumptions.
   - Confirm whether dependencies already exist in this project.
   - Mark required supporting files such as `common/registry.py`, `common/worktree.py`, or `common/hooks.py`.
3. Decide import set:
   - Prefer the smallest set that supports `spec_wiki.py` and hook-runner behavior.
   - Keep multi-agent helpers optional unless a current workflow hook or test needs them.
4. Copy approved infrastructure files with minimal changes:
   - Preserve current project command conventions.
   - Do not copy project-specific state or business rules.
   - Do not copy generated `.pyc` files.
5. Adapt workflow/spec docs only if needed:
   - Add `spec_wiki.py index/lint/log` references only if `spec_wiki.py` is imported and validated.
   - Do not replace current FastAPI/React spec guidance with `.trellis-other` JSE guidance.
6. Add or port tests:
   - Import only reusable `.trellis-other/tests/**` cases.
   - Update assertions to match current project paths and Codex inline mode.
7. Validate:
   - `python ./.trellis/scripts/task.py current --source`
   - `python ./.trellis/scripts/get_context.py --mode phase`
   - If adopted: `python ./.trellis/scripts/spec_wiki.py index`
   - If adopted: `python ./.trellis/scripts/spec_wiki.py lint`
   - If tests are adopted: run the focused pytest command for `.trellis/tests`
8. Review diff:
   - Confirm no `.trellis-other/tasks/**`, `.trellis-other/workspace/**`, `.trellis-other/.runtime/**`, `.developer`, or JSE business specs were copied.
   - Confirm only task artifacts and approved infrastructure files changed.

## Validation Notes

The first implementation pass should be considered incomplete unless every imported script either runs successfully or has a documented, concrete blocker. If `spec_wiki.py lint` reports existing spec debt, capture the findings rather than hiding them.

## Stop Gate

Do not run `task.py start` for this task until the user has reviewed `prd.md`, `design.md`, and `implement.md` and asks to proceed.
