# Implementation Spec - Trellis Codex Hooks And Subagents

## Goal Summary

Implement Codex hook support for Trellis context injection without changing the default Codex `inline` workflow. The implementation should make future `sub-agent` mode reliable while keeping inline mode simple and stable.

## Planned Changes

- Add or update `.codex/hooks/inject-subagent-context.py`.
- Update `.codex/hooks.json` to register:
  - `SessionStart`
  - `UserPromptSubmit`
  - `SubagentStart`
- Update `.codex/config.toml` comments so they match current Codex hook behavior:
  - Hooks are enabled by default.
  - Project hooks require trusted project config.
  - Non-managed hooks require `/hooks` review before running.
- Keep `.trellis/config.yaml` default effectively `inline`; do not uncomment or set `codex.dispatch_mode: sub-agent` by default.
- Add tests under `.trellis/tests/` or another agreed test location for hook scripts and config shape.
- Update LLM-Wiki pages if implementation decisions differ from this spec.

## Detailed Implementation Notes

### Hook Registration

- Prefer `hooks.json` over inline `[hooks]` in `.codex/config.toml` to avoid duplicate hook-source warnings.
- Use git-root-stable commands if feasible, because Codex may start from a subdirectory.
- Keep Windows-compatible command forms, using `python -X utf8`.
- Do not add `SubagentStop` unless a future task defines an explicit audit-only contract.

### Subagent Context Hook

- Use existing `.codex/hooks/session-start.py` and `.codex/hooks/inject-workflow-state.py` patterns for:
  - repo root discovery
  - safe file reads
  - JSON output
  - readable failure messages
- Do not duplicate large Trellis task parsing logic when existing `.trellis/scripts/common/*` modules can be imported safely.
- Treat missing active task as a visible context warning, not a hard crash.
- Treat seed-only JSONL manifests as valid but low-context; subagents already have fallback instructions.

### Dispatch Mode Behavior

- `inline`:
  - User prompt breadcrumbs should say the main session implements/checks directly.
  - Main session should use `trellis-before-dev`, `trellis-check` skill, validation, `trellis-update-spec`, commit, and finish-work.
  - Do not dispatch implement/check subagents.
- `sub-agent`:
  - User prompt breadcrumbs may instruct main session to dispatch Trellis subagents.
  - Dispatch prompt must start with `Active task: <task path>`.
  - `SubagentStart` may provide context, but each agent must retain agent-pull fallback.

### Safety Rules

- Do not modify `.trellis/scripts` unless tests prove an existing script cannot support the hook integration.
- Do not add lifecycle behavior that automatically retries, redispatches, or closes subagents.
- Preserve the current recursion guard in `.codex/agents/*.toml`.
- Keep subagent multi-agent features disabled inside Trellis subagents.

## Rollout Plan

1. Add tests first for expected hook manifest and current hook outputs.
2. Implement `inject-subagent-context.py`.
3. Register `SessionStart` and `SubagentStart` in `.codex/hooks.json`.
4. Update `.codex/config.toml` comments.
5. Run tests and manually inspect `/hooks` state in Codex.
6. Keep `codex.dispatch_mode` as `inline` unless explicitly testing subagent mode.

## Non-Goals

- No runtime application feature work.
- No Trellis upstream template changes unless a separate task scopes template synchronization.
- No default switch to subagent dispatch.
- No Claude/Cursor/OpenCode hook changes in this Codex-focused task.

