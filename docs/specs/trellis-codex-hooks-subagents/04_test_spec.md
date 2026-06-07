# Test Spec - Trellis Codex Hooks And Subagents

## Validation Scope

Validate that Codex/Trellis hook integration is configured correctly, produces valid hook output, preserves inline default behavior, and keeps subagent mode safe when explicitly enabled.

## Automated Tests

- TC1: Hook manifest parses as JSON and contains `UserPromptSubmit`.
- TC2: Hook manifest contains `SessionStart` with matcher `startup|resume|clear|compact` after implementation.
- TC3: Hook manifest contains `SubagentStart` with matcher `trellis-research|trellis-implement|trellis-check` after implementation.
- TC4: Hook manifest does not contain `SubagentStop` by default.
- TC5: `inject-workflow-state.py` emits inline mode banner when `codex.dispatch_mode` is missing or invalid.
- TC6: `inject-workflow-state.py` emits sub-agent mode banner only when `.trellis/config.yaml` explicitly sets `codex.dispatch_mode: sub-agent`.
- TC7: `session-start.py` emits valid Codex hook JSON for startup/resume/clear/compact-like inputs.
- TC8: `inject-subagent-context.py` ignores non-Trellis subagent types.
- TC9: `inject-subagent-context.py` emits context for `trellis-implement` from active task artifacts and `implement.jsonl`.
- TC10: `inject-subagent-context.py` emits context for `trellis-check` from active task artifacts and `check.jsonl`.
- TC11: `inject-subagent-context.py` emits context for `trellis-research` and preserves research-only write guidance.
- TC12: Agent TOML files keep `[features] multi_agent = false` and `[features.multi_agent_v2] enabled = false`.

## Manual Verification

- MV1: Start a trusted Codex session and confirm `/hooks` shows project hooks pending review or trusted.
- MV2: In default inline mode, confirm workflow breadcrumbs say the main session implements/checks directly.
- MV3: In default inline mode, confirm the main session does not dispatch `trellis-implement` or `trellis-check`.
- MV4: Temporarily set `codex.dispatch_mode: sub-agent` in a controlled branch and confirm breadcrumbs switch to sub-agent mode.
- MV5: Spawn a `trellis-research` agent and confirm it receives or can pull the active task and writes only under `{TASK_DIR}/research/`.
- MV6: Spawn `trellis-implement` / `trellis-check` only in explicit sub-agent test mode and confirm they do not recursively spawn more agents.
- MV7: Confirm completed subagents naturally return results to the parent; do not rely on `SubagentStop` for closure.

## Regression Checks

- RC1: `python ./.trellis/scripts/task.py current --source` still works.
- RC2: Existing `.codex/hooks/inject-workflow-state.py` behavior remains backward-compatible.
- RC3: `.trellis/scripts` has no unrelated changes.
- RC4: LLM-Wiki index still links `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`.

## Acceptance Review

- Reviewers should compare implementation against:
  - `docs/specs/trellis-codex-hooks-subagents/01_requirement.md`
  - `docs/specs/trellis-codex-hooks-subagents/02_interface.md`
  - `docs/specs/trellis-codex-hooks-subagents/03_implementation.md`
  - `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`

