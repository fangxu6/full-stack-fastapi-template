# Design: Extensible project quality hooks

## Boundary

The implementation is entirely project-owned under `hooks/**`. Trellis library
files and Trellis configuration are immutable dependencies, not extension
points. A future Codex or CI adapter can invoke the project CLI, but no platform
lifecycle event is assumed by this task.

## Architecture

| Component | Responsibility |
| --- | --- |
| `hooks/quality_hooks/contracts.py` | Defines `HookContext`, `HookResult`, and the `QualityHook` protocol. |
| `hooks/quality_hooks/registry.py` | Owns project default hook registration and unknown-hook validation. |
| `hooks/quality_hooks/changed_files.py` | Reads tracked and untracked worktree paths from Git. |
| `hooks/quality_hooks/backend.py` | Runs backend checks only for backend changes or `--force`. |
| `hooks/quality_hooks/frontend.py` | Enforces frontend component-system rules only for frontend changes or `--force`. |
| `hooks/run_quality_hooks.py` | Stable human/automation CLI entrypoint. |

## Interface Contract

```python
class QualityHook(Protocol):
    name: str
    def applies(self, context: HookContext) -> bool: ...
    def run(self, context: HookContext) -> HookResult: ...
```

`HookContext` contains the repository root, changed paths, and an explicit
force flag. `HookResult` is `passed`, `failed`, or `skipped`; only failed
results make the CLI return non-zero.

Run all applicable hooks after development:

```powershell
python hooks/run_quality_hooks.py
```

Run a required final backend check even after changes were staged or committed:

```powershell
python hooks/run_quality_hooks.py --hook backend-quality --force
```

## Backend Policy

POSIX hosts invoke `backend/scripts/lint.sh` from the backend directory. Windows
hosts use the repository `.venv/Scripts/python.exe` to execute the exact mypy,
ty, Ruff, and format-check commands from that script. This avoids WSL PATH
translation and does not depend on `backend/.venv`.

## Frontend Policy

The hook reads `frontend/components.json` for `aliases.ui` and applies the
existing project component rules: generated UI/client files are protected,
components must stay under allowed roots, Ant Design belongs only in complex
surface roots, shared code cannot import feature/platform paths, and a UI alias
import must resolve to an existing primitive.

## Extensibility

Add a new hook by implementing `QualityHook` in `hooks/quality_hooks/` and
adding one instance to `default_registry()`. No Trellis update can overwrite
this extension surface.

## Rollback

Delete the new project hook package and runner. No Trellis state, library files,
or application source needs restoration.
