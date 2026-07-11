# Extensible project quality hooks

## Goal

Introduce a project-owned hook interface for post-development quality checks.
It must be safe from Trellis library updates and make future hooks easy to add.

## Confirmed Facts

- `.trellis/scripts/common/config.py`, `.trellis/scripts/common/task_utils.py`,
  and `task.py` are Trellis library files and must not be changed for this work.
- The repository root already owns a `hooks/` directory, so it is the stable
  location for project quality hooks.
- Backend validation uses strict mypy, ty, Ruff, and Ruff format checks.
- Frontend component rules live in `.trellis/spec/frontend/**`; the active UI
  alias is defined in `frontend/components.json`.

## Requirements

1. Provide a typed `QualityHook` interface, execution context, result type, and
   registry under `hooks/quality_hooks/`.
2. Provide `python hooks/run_quality_hooks.py` as the only execution entrypoint.
   It discovers changed files by default and supports named hooks, explicit
   changed paths, `--force`, text output, and JSON output.
3. Add a backend hook that runs the maintained backend quality commands. On
   Windows it must use the root `.venv/Scripts/python.exe`, never `backend/.venv`.
4. Add a frontend component-policy hook that rejects generated/vendor edits,
   invalid component placement, invalid Ant Design placement, domain imports in
   shared components, and unresolved UI primitive imports.
5. Keep all Trellis library files and `.trellis/config.yaml` unchanged.
6. Make adding a future hook a project-local change: implement the interface and
   register it in the project registry.

## Acceptance Criteria

- [ ] No diffs remain in `.trellis/scripts/common/config.py`,
  `.trellis/scripts/common/task_utils.py`, `.trellis/scripts/task.py`, or
  `.trellis/config.yaml`.
- [ ] `python hooks/run_quality_hooks.py --list` reports the default hooks.
- [ ] A failing selected hook returns a non-zero process result; skipped hooks
  do not fail the command.
- [ ] Backend hook uses root `.venv` on Windows and exposes missing-tool output.
- [ ] Frontend hook accepts a registered UI primitive and rejects each protected
  component-system violation.
- [ ] Focused hook tests pass.

## Out Of Scope

- Modifying Trellis library lifecycle behavior.
- Automatically registering unsupported Codex lifecycle events.
- Rewriting backend or frontend application code.
