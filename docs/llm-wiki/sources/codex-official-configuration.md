---
title: Codex official configuration source
created: 2026-06-07
updated: 2026-08-17
type: source
tags:
  - llm-wiki
  - codex
  - config
  - hooks
  - subagents
  - rules
status: active
source_count: 5
---

# Codex Official Configuration Source

## Source

- Path: `docs/llm-wiki/sources/codex/Advanced Configuration – Codex  OpenAI Developers.md`
- Path: `docs/llm-wiki/sources/codex/Configuration Reference – Codex  OpenAI Developers.md`
- Path: `docs/llm-wiki/sources/codex/Hooks – Codex  OpenAI Developers.md`
- Path: `docs/llm-wiki/sources/codex/Subagents – Codex  OpenAI Developers.md`
- Path: `docs/llm-wiki/sources/codex/Rules – Codex  OpenAI Developers.md`
- Role: Local clippings of OpenAI Codex documentation for configuration, hooks, subagents, and command rules.

## Key Facts

- Codex has layered configuration. User-level configuration lives under `CODEX_HOME` such as `~/.codex/config.toml`, while project-scoped `.codex/config.toml` loads only when the project is trusted.
- Project-scoped Codex config cannot override machine-local provider, auth, notification, profile-selection, or telemetry-routing settings. Those belong in user-level configuration.
- Profiles are separate `$CODEX_HOME/<profile>.config.toml` layers selected with `--profile <profile>`.
- Project root detection controls where Codex looks for `.codex/` configuration layers and `AGENTS.md`; it defaults to `.git` and can be customized with `project_root_markers`.
- Lifecycle hooks can be declared in `hooks.json` or inline `[hooks]` tables next to active config layers. Codex loads all matching hooks rather than replacing lower-precedence hooks.
- Project-local hooks, rules, and project config load only when the project `.codex/` layer is trusted. User and managed layers are separate.
- Non-managed command hooks require review and trust before they run; managed hooks from requirements or enterprise channels are trusted by policy.
- Hooks are event based. Important events include `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, and `Stop`.
- `PreToolUse`, `PermissionRequest`, and `PostToolUse` match tool names such as `Bash`, `apply_patch`, and MCP tool names. `SubagentStart` and `SubagentStop` match subagent type.
- Only command hook handlers run today. Prompt and agent hook handlers are parsed but skipped.
- Codex subagents are spawned only when explicitly requested. They inherit the parent sandbox policy and live runtime overrides, and their work consumes additional tokens.
- Custom agents are standalone TOML files under `~/.codex/agents/` or `.codex/agents/` and must define `name`, `description`, and `developer_instructions`.
- Global subagent settings under `[agents]` include `max_threads`, `max_depth`, and `job_max_runtime_seconds`.
- Codex command rules live in `.rules` files under a `rules/` directory beside an active config layer. Rules use `prefix_rule()` to allow, prompt, or forbid commands outside the sandbox.
- When multiple rules match, Codex applies the most restrictive decision: `forbidden` wins over `prompt`, which wins over `allow`.
- Codex can split simple shell-wrapper scripts into individual commands before applying rules, but treats scripts with advanced shell features as one conservative wrapper invocation.

## Durable Guidance

- Use project-local `.codex/config.toml`, hooks, rules, and agents only for repository-scoped behavior that should be active after the project is trusted.
- Keep provider credentials, base URLs, telemetry, notifications, and personal profiles in user-level configuration.
- Use `AGENTS.md` for durable repository instructions and `.codex/config.toml` for Codex runtime configuration; do not collapse those surfaces into one file.
- Use hooks for deterministic lifecycle checks or context injection, especially when the behavior must happen around tool calls, prompts, session start, compaction, or subagent lifecycle events.
- Use rules for command-execution policy outside the sandbox, not for general coding style or workflow narration.
- Use custom agents for specialized subagent roles only when parallel or isolated work is worth the extra token and orchestration cost.
- This repository's dispatch behavior is a local Trellis contract, not an OpenAI Codex setting: missing `codex.dispatch_mode` defaults to `auto`, `inline` is an explicit opt-out, and `sub-agent` is a compatibility alias for `auto`. Source: [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]], `.trellis/config.yaml`, and `.codex/hooks/inject-workflow-state.py`.

## Constraints And Risks

- Codex docs describe several features as experimental or evolving, including command rules and subagent CSV fan-out. Treat detailed syntax as version-sensitive.
- `PreToolUse` is a guardrail, not a complete enforcement boundary; equivalent work may be possible through another tool path.
- `PostToolUse` cannot undo side effects because the tool has already run.
- `SubagentStart` can add context for a subagent but does not stop the subagent from starting.
- `SubagentStop` can observe or continue a subagent flow, but it should not be treated as the normal close mechanism.
- Project-local hooks and rules do not apply in untrusted projects.

## Related Pages

- [[docs/llm-wiki/entities/codex|Codex]]
- [[docs/llm-wiki/entities/trellis|Trellis]]
- [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]]
