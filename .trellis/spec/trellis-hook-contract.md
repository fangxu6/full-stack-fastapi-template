# Project Quality Hook Contract

> Executable contract for project-owned post-development checks under `hooks/**`.

---

## 1. Scope / Trigger

- Trigger: adding a reusable backend/frontend quality check or invoking required
  checks after development.
- Primary files: `hooks/quality_hooks/**`, `hooks/run_quality_hooks.py`.
- Out of scope: `.trellis/scripts/common/**`, `.trellis/scripts/task.py`,
  `.trellis/config.yaml`, and automatic Trellis task lifecycle changes.

---

## 2. Signatures / Interfaces

- `python hooks/run_quality_hooks.py [--hook NAME] [--force] [--changed-file PATH] [--json]`
- `.codex/hooks/stop-quality-gate.py` maps the runner result to Codex `Stop`.
- `QualityHook.applies(context: HookContext) -> bool`
- `QualityHook.run(context: HookContext) -> HookResult`
- Register project defaults only in `default_registry()`.

---

## 3. Contracts

- `HookResult.status` is `passed`, `failed`, `pending`, or `skipped`; the CLI
  fails only when at least one selected hook fails.
- Generated client or route-tree output is `pending`, not a quality failure:
  it keeps the Phase 3.4 dedicated synchronization commit visible without
  blocking Codex Stop before the user can confirm that commit.
- The runner gets worktree paths from Git unless callers supply
  `--changed-file`; `--force` overrides scope matching.
- Windows backend checks run from `backend/` using root
  `.venv/Scripts/python.exe`. They never use `backend/.venv`.
- Frontend UI imports are resolved through `frontend/components.json`.
- Future hooks are project code and registry entries, never Trellis library
  edits.
- The Codex Stop adapter returns `{}` after passing, pending, or skipped
  checks. On failure it returns `decision: block` with a reason so Codex
  continues instead of completing the turn.

---

## 4. Validation & Error Matrix

| Condition | Expected Behavior | Verification |
| --- | --- | --- |
| Non-matching worktree changes | Hook is skipped | Unit test |
| Backend diagnostic or missing root tooling | Backend result fails; CLI returns non-zero | Stubbed failure test / forced CLI |
| Generated client or route-tree output | Frontend result is pending; CLI exits zero | Unit and Stop-adapter tests |
| Vendor-managed primitive or structural frontend violation | Frontend result fails | Unit test |
| Unknown selected hook | CLI/registry rejects it | Unit test |
| New project hook | Registered implementation runs without Trellis changes | Registry test and protected-file diff check |
| Quality hook fails during Codex Stop | Adapter returns `decision: block` with diagnostics | Adapter unit test |

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
