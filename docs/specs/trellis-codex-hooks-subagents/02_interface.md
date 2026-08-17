# Current Interface - Trellis Codex Hooks And Subagents

## Overview

本文记录已部署的 Codex/Trellis 本地配置接口、hook 输入输出约定和兼容边界；不新增应用运行时 API。

## Configuration Interface

### `.trellis/config.yaml`

- `codex.dispatch_mode`:
  - Missing: treated as `auto`.
  - `auto`: main Codex session coordinates and Trellis dispatches research, implementation, and check roles.
  - `inline`: main Codex session implements and checks directly.
  - `sub-agent`: backwards-compatible alias for `auto`.
  - Invalid explicit value: treated as `inline`.

### `.codex/hooks.json`

Current hook registrations:

- `UserPromptSubmit`
  - Command: `python3 -X utf8 .codex/hooks/inject-workflow-state.py`.
  - Purpose: inject per-turn workflow-state and codex-mode banner.
- `SubagentStart`
  - Matcher: `^(?:trellis-implement|trellis-check|trellis-research)$`.
  - Command: `python3 -X utf8 .codex/hooks/inject-subagent-context.py`.
  - Purpose: inject active task context for supported Trellis subagents.
- `Stop`
  - Command: `python3 -X utf8 .codex/hooks/stop-quality-gate.py`.
  - Purpose: run the final quality gate.

`SubagentStop` is not registered by default.

## Hook Output Contract

### Workflow-State Injection

`inject-workflow-state.py` normalizes dispatch mode once for both its mode banner and breadcrumb key. `auto` emits the native-dispatch path; `inline` emits the main-session path.

### `inject-subagent-context.py`

- Accepts only recognised native `SubagentStart` events and supported Trellis roles.
- Resolves the active task from the parent session without borrowing another Codex session's task.
- For implement/check roles, reads the role-specific JSONL manifest followed by `prd.md`, optional `design.md`, and optional `implement.md`; configured byte limits bound the injected payload.
- Emits Codex `hookSpecificOutput` with `hookEventName: SubagentStart` and additional context. A hook failure never prevents the native subagent from starting.
- The injected instruction prohibits nested Trellis subagent dispatch; each role keeps its child-side context-loading fallback.

## Agent Interfaces

### `.codex/agents/trellis-research.toml`

- Read-heavy researcher.
- Writes only under `{TASK_DIR}/research/`.
- Keeps multi-agent features disabled inside the subagent.

### `.codex/agents/trellis-implement.toml`

- Workspace-write implementer.
- Loads active task and implementation context before editing.
- Keeps multi-agent features disabled inside the subagent.

### `.codex/agents/trellis-check.toml`

- Workspace-write reviewer/checker.
- Reviews and fixes directly.
- Keeps multi-agent features disabled inside the subagent.

## Public Compatibility

- No backend/frontend runtime behavior changes.
- No HTTP API, database, route, or generated client changes.
- Explicit `inline` remains available when main-session implementation/checking is required.

## Source References

- Local durable query: `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`.
- Local implementation: `.trellis/config.yaml`, `.codex/hooks.json`, `.codex/hooks/inject-workflow-state.py`, `.codex/hooks/inject-subagent-context.py`, `.codex/agents/*.toml`.
- Official docs: OpenAI Codex hooks/subagents and Trellis configuration/workflow documentation.
