# Project Quality Hook Contract

> Executable contract for project-owned post-development checks under `hooks/**`.

---

## 1. Scope / Trigger

- Trigger: adding a reusable backend/frontend quality check or invoking required
  checks after development.
- Primary files: `hooks/quality_hooks/**`, `hooks/run_quality_hooks.py`.
- Out of scope: `.trellis/scripts/common/**`, `.trellis/scripts/task.py`,
  `.trellis/config.yaml`, and automatic Codex lifecycle registration.

---

## 2. Signatures / Interfaces

- `python hooks/run_quality_hooks.py [--hook NAME] [--force] [--changed-file PATH] [--json]`
- `QualityHook.applies(context: HookContext) -> bool`
- `QualityHook.run(context: HookContext) -> HookResult`
- Register project defaults only in `default_registry()`.

---

## 3. Contracts

- `HookResult.status` is `passed`, `failed`, or `skipped`; the CLI fails only
  when at least one selected hook fails.
- The runner gets worktree paths from Git unless callers supply
  `--changed-file`; `--force` overrides scope matching.
- Windows backend checks run from `backend/` using root
  `.venv/Scripts/python.exe`. They never use `backend/.venv`.
- Frontend UI imports are resolved through `frontend/components.json`.
- Future hooks are project code and registry entries, never Trellis library
  edits.

---

## 4. Validation & Error Matrix

| Condition | Expected Behavior | Verification |
| --- | --- | --- |
| Non-matching worktree changes | Hook is skipped | Unit test |
| Backend diagnostic or missing root tooling | Backend result fails; CLI returns non-zero | Stubbed failure test / forced CLI |
| Protected frontend primitive/client edit | Frontend result fails | Unit test |
| Unknown selected hook | CLI/registry rejects it | Unit test |
| New project hook | Registered implementation runs without Trellis changes | Registry test and protected-file diff check |

---

## 5. Good / Base / Bad Cases

- Good: implement and register a focused project `QualityHook`.
- Base: invoke one named hook explicitly with `--hook` and `--force`.
- Bad: modify Trellis `common/config.py` or `common/task_utils.py` to add a
  project policy.

---

## 6. Tests Required

- Run `python -m unittest discover hooks/tests -v`.
- Check `python hooks/run_quality_hooks.py --list`.
- Verify no diff for the protected Trellis library/configuration files.
- Add pass, failure, and skip coverage for every new hook.

---

## 7. Wrong vs Correct

### Wrong

Add structured policy parsing or blocking behavior to
`.trellis/scripts/common/config.py` or `common/task_utils.py`.

### Correct

Implement the check under `hooks/quality_hooks/`, add it to
`default_registry()`, and call it through `hooks/run_quality_hooks.py`.
