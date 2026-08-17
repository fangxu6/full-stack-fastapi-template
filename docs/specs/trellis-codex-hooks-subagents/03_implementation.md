# Implementation Record - Trellis Codex Hooks And Subagents

## Goal Summary

The Codex hook integration is implemented. It provides Trellis context injection for native subagents while keeping `inline` available as an explicit main-session mode; missing dispatch configuration defaults to `auto`.

## Implemented Components

- `.codex/hooks/inject-subagent-context.py` materializes role-specific JSONL context and task artifacts for native `SubagentStart` events.
- `.codex/hooks.json` registers `UserPromptSubmit`, scoped `SubagentStart`, and `Stop` handlers.
- `.codex/hooks/inject-workflow-state.py` normalizes `auto`, `inline`, and the `sub-agent` compatibility alias for both banner and breadcrumb behavior.
- `.codex/agents/trellis-*.toml` keep role boundaries and child-side context fallback available if native injection is unavailable.
- `.trellis/config.yaml` documents the default and payload-limit configuration comments.

## Dispatch Mode Behavior

- `auto` (default): the main session coordinates; Trellis dispatches research, implementation, and check roles. Native `SubagentStart` injection is preferred and child-side loading is the fallback.
- `inline`: the main session implements and checks directly. Do not dispatch implement/check subagents.
- `sub-agent`: legacy alias for `auto`.
- Invalid explicit values: safely use `inline`.

## Safety Rules

- Do not add lifecycle behavior that automatically retries, redispatches, or closes subagents.
- Preserve the recursion guard in the injected native subagent context and keep subagent multi-agent features disabled.
- Keep task-context byte limits in effect so automatic dispatch does not inject unbounded context.

## Verification Status

- The hook manifest and implementation files above are the source of truth for the deployed behavior.
- Repository inspection found no direct automated test covering `_resolve_codex_dispatch_mode` or native `SubagentStart` context injection. `04_test_spec.md` records the regression checks that should cover this contract when test coverage is added or refreshed.

## Non-Goals

- No runtime application feature work.
- No Trellis upstream template changes unless a separate task scopes template synchronization.
- No automatic lifecycle control through `SubagentStop`.
- No Claude/Cursor/OpenCode hook changes in this Codex-focused integration.
