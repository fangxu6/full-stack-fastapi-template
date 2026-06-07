---
title: Codex
created: 2026-06-07
updated: 2026-06-07
type: entity
tags:
  - llm-wiki
  - codex
  - agent
  - workflow
status: active
---

# Codex

## Summary

Codex is the coding-agent runtime used in this repository. Its durable customization surfaces include repository instructions, layered config, lifecycle hooks, custom subagents, command rules, MCP/app integrations, skills, plugins, and automations.

## Repository-Relevant Surfaces

- `AGENTS.md`: repository guidance that Codex reads as project instructions.
- `.codex/config.toml`: trusted project-scoped runtime configuration for Codex settings that belong to this repository.
- `.codex/hooks.json` or inline `[hooks]`: deterministic lifecycle scripts loaded beside active config layers.
- `.codex/agents/*.toml`: project-scoped custom subagents, each defined as a standalone TOML config layer.
- `.codex/rules/*.rules`: project-scoped command prefix policy, loaded only when the project `.codex/` layer is trusted.
- Skills and plugins: reusable task workflows and installable bundles. Use them when behavior should be reusable beyond a single prompt.

## Durable Rules

- Keep personal or machine-local provider, auth, notification, profile, and telemetry settings out of project `.codex/config.toml`; Codex ignores several such keys when they appear in project-local config.
- Prefer the smallest customization surface: prompt for one-off constraints, `AGENTS.md` for durable repo conventions, `.codex/config.toml` for runtime configuration, hooks for deterministic lifecycle behavior, rules for command policy, and custom agents for explicit subagent roles.
- Treat project-local `.codex/` behavior as trust-gated. Hooks, rules, and project config are skipped until the project layer is trusted.
- Scope hooks by their native Codex matcher semantics. `PreToolUse` matches tool names; `SubagentStart` and `SubagentStop` match subagent type.
- Use command rules to control commands outside the sandbox. Use hook scripts or Trellis skills for workflow context and validation.
- Keep subagent workflows explicit. Codex only spawns subagents when asked, and this repository's Trellis default remains inline execution unless a user opts into subagent dispatch.

## Local Integration Guidance

- For Trellis context injection into Codex subagents, prefer `SubagentStart` over `PreToolUse`.
- Do not use `SubagentStop` as the default close mechanism for Trellis subagents. Codex orchestration owns waiting for and collecting subagent results.
- Use `SessionStart` or `UserPromptSubmit` hooks only when deterministic Trellis breadcrumbs are needed in every relevant Codex session or turn.
- When adding `.rules`, include `match` and `not_match` examples so Codex validates the policy at startup.

## Sources

- [[docs/llm-wiki/sources/codex-official-configuration|Codex official configuration source]]
- [[docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode|Trellis Codex hooks and dispatch mode]]
