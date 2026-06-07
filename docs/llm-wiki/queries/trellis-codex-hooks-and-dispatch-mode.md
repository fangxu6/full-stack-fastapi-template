---
title: Trellis Codex hooks and dispatch mode
created: 2026-06-07
updated: 2026-06-07
type: query
tags:
  - llm-wiki
  - trellis
  - codex
  - hooks
  - subagents
status: active
---

# Trellis Codex Hooks And Dispatch Mode

## Question

How should this repository integrate Trellis beta workflows with Codex hooks and Codex subagents, especially around `PreToolUse`, `SubagentStart`, `SubagentStop`, and `codex.dispatch_mode`?

## Answer

Use Codex's native hook model instead of copying Claude Code hook names one-for-one. For this repository, Codex subagent context should be attached at `SubagentStart`, while `PreToolUse` should remain a tool-call guardrail hook for tools such as `Bash`, `apply_patch`, and MCP tools.

Keep Trellis `codex.dispatch_mode` defaulted to `inline`. Only use `sub-agent` when the user explicitly opts into Trellis subagent dispatch.

## Durable Claims

- Codex supports `PreToolUse`, but `PreToolUse(Task/Agent)` is a Claude Code pattern, not the Codex subagent context-injection path. Source: OpenAI Codex hooks documentation; local comparison of `.claude/settings.json` and `.codex/hooks.json`.
- Codex `PreToolUse` matchers filter tool names. This makes it useful for command, edit, and MCP policy checks, but not for Trellis subagent startup context. Source: OpenAI Codex hooks documentation.
- Codex `SubagentStart` matchers filter subagent type. This is the correct Codex event for injecting Trellis active task context into `trellis-research`, `trellis-implement`, and `trellis-check`. Source: OpenAI Codex hooks documentation; local `.codex/agents/*.toml`.
- `SubagentStart` cannot guarantee a subagent closes. It runs at subagent start scope and should be treated as startup context or validation. Source: OpenAI Codex hooks documentation.
- Subagent shutdown is handled by Codex orchestration when the parent workflow waits for and collects subagent results. Source: OpenAI Codex subagents documentation.
- `SubagentStop` is an observation or post-stop hook, not a close mechanism. Do not default it for automatic close, automatic redispatch, or Ralph Loop style retry. Source: OpenAI Codex hooks documentation; Trellis beta workflow direction discussed in this query.
- Trellis `codex.dispatch_mode` should remain `inline` by default. In this mode, the main Codex session implements and checks directly, using Trellis skills and artifacts for context. Source: Trellis configuration and beta workflow documentation; local `.trellis/config.yaml` and `.trellis/workflow.md`.
- Trellis `codex.dispatch_mode: sub-agent` is an explicit opt-in mode where the main Codex session coordinates and dispatches `trellis-implement`, `trellis-check`, or `trellis-research`. Source: Trellis configuration and beta workflow documentation; local `.codex/agents/*.toml`.

## Local Implementation Guidance

- Register `UserPromptSubmit` for per-turn Trellis workflow breadcrumbs.
- Register `SessionStart` when the project wants new Codex sessions to receive a Trellis overview.
- Register `SubagentStart` for `trellis-research|trellis-implement|trellis-check` only when `codex.dispatch_mode: sub-agent` is supported by the local workflow.
- Do not register `SubagentStop` by default. Add it later only for lightweight audit logging or post-run validation.
- Do not copy Claude Code's `PreToolUse` matcher values `Task` or `Agent` into Codex. If Codex `PreToolUse` is used, scope it to actual Codex tool names.
- Keep `.trellis/scripts` out of this integration unless a future Trellis task explicitly requires script-level changes.

## Mode Comparison

| Mode | Main behavior | Context strategy | Default |
| --- | --- | --- | --- |
| `inline` | Main Codex session implements and checks directly. | Main session reads `prd.md`, optional `design.md`, optional `implement.md`, specs, and research through Trellis skills. | Yes |
| `sub-agent` | Main Codex session coordinates; Trellis subagents perform research, implementation, or checking. | Subagents load context from dispatch prompt, `task.py current --source`, task artifacts, and JSONL manifests; `SubagentStart` may inject extra context. | No |

## Sources

- Conversation source: user questions in the current Codex thread about Trellis hooks, Codex hooks, `PreToolUse(Task/Agent)`, `SubagentStart`, `SubagentStop`, and `codex.dispatch_mode`.
- Local files: `.claude/settings.json`, `.codex/hooks.json`, `.codex/config.toml`, `.codex/agents/*.toml`, `.trellis/config.yaml`, `.trellis/workflow.md`, `docs/llm-wiki/SCHEMA.md`.
- Official docs: [Trellis configuration](https://docs.trytrellis.app/advanced/configuration), [Trellis beta how it works](https://docs.trytrellis.app/beta/start/how-it-works), [Trellis v0.6.0-beta.1 changelog](https://docs.trytrellis.app/changelog/v0.6.0-beta.1), [OpenAI Codex hooks](https://developers.openai.com/codex/hooks), [OpenAI Codex subagents](https://developers.openai.com/codex/subagents).

## Open Questions

- Whether this repository should eventually enable `SubagentStart` in `.codex/hooks.json` depends on choosing `codex.dispatch_mode: sub-agent`; the current default remains `inline`.
- If post-run audit is needed later, define a narrow `SubagentStop` contract that records completion without redispatching or attempting lifecycle control.
