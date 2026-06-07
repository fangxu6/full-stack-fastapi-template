# Interface Spec - Trellis Codex Hooks And Subagents

## Overview

本方案主要改变 Codex/Trellis 的本地配置接口、hook 输入输出约定和测试入口，不新增应用运行时 API。

## Configuration Interfaces

### `.trellis/config.yaml`

- `codex.dispatch_mode`:
  - Missing or invalid: treated as `inline`.
  - `inline`: main Codex session implements and checks directly.
  - `sub-agent`: main Codex session may dispatch Trellis subagents.

### `.codex/hooks.json`

Target hook registrations:

- `SessionStart`
  - Matcher: `startup|resume|clear|compact`.
  - Command: `python -X utf8 .codex/hooks/session-start.py`.
  - Purpose: inject Trellis session overview.
- `UserPromptSubmit`
  - No matcher, because Codex ignores matcher for this event.
  - Command: `python -X utf8 .codex/hooks/inject-workflow-state.py`.
  - Purpose: inject per-turn workflow-state and codex-mode banner.
- `SubagentStart`
  - Matcher: `trellis-research|trellis-implement|trellis-check`.
  - Command: `python -X utf8 .codex/hooks/inject-subagent-context.py`.
  - Purpose: inject or validate Trellis task context for Codex subagents.

Do not register `SubagentStop` by default.

## Hook Output Contracts

### Codex Context Injection

Hook scripts should emit valid Codex hook JSON with additional context in the documented Codex shape. The implementation should preserve existing `hookSpecificOutput.hookEventName` behavior for `UserPromptSubmit`.

### `inject-subagent-context.py`

Required behavior:

- Parse Codex hook stdin defensively.
- Resolve subagent type from documented `SubagentStart` fields and tolerate compatible aliases if present.
- Ignore non-Trellis subagents.
- Resolve active task using the same session-aware task lookup used by existing hooks.
- Load task context in this order:
  - `prd.md`
  - `design.md` if present
  - `implement.md` if present
  - `implement.jsonl` or `check.jsonl` depending on subagent type
  - referenced spec/research files from JSONL entries with `file`
- Include recursion guard:
  - `trellis-implement` must not spawn `trellis-implement` or `trellis-check`.
  - `trellis-check` must not spawn `trellis-check` or `trellis-implement`.
  - `trellis-research` must not edit code or spawn implementation/check agents.

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
- Existing `inline` Codex workflow remains the default and must continue to work if all new subagent hooks are disabled or untrusted.

## Source References

- Local durable query: `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`.
- Local Trellis workflow: `.trellis/workflow.md`.
- Local Codex hooks and agents: `.codex/hooks.json`, `.codex/hooks/*.py`, `.codex/agents/*.toml`.
- Official docs: OpenAI Codex hooks/subagents and Trellis beta configuration/workflow documentation.

