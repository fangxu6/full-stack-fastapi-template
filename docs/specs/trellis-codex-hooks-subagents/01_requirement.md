# Requirement Spec - Trellis Codex Hooks And Subagents

## Background

- 当前项目已经接入 Trellis beta，并存在 `.codex/hooks.json`、`.codex/hooks/*.py`、`.codex/agents/*.toml`、`.trellis/workflow.md` 等 Codex/Trellis 集成文件。
- 本轮讨论只完成了方案研究和 LLM-Wiki 知识沉淀，尚未真正实施 Codex hooks 与 Trellis subagent 的落地改造。
- 后续仍需要在保持 `codex.dispatch_mode` 默认 `inline` 的前提下，补齐可选 `sub-agent` 模式的 hook、测试与文档化能力。

## Goals

- 为后续实施 Trellis/Codex hooks 与 subagents 提供可接续的本地方案。
- 明确 Codex hooks 与 Claude Code hooks 的差异，避免把 Claude 的 `PreToolUse(Task/Agent)` 直接迁移到 Codex。
- 保持 Codex 默认 `inline`：主会话直接实现、检查，不默认派发 `trellis-implement` / `trellis-check`。
- 在显式设置 `codex.dispatch_mode: sub-agent` 时，支持 Codex `SubagentStart` 为 Trellis subagents 注入或校验任务上下文。
- 为 hooks 和 agent 配置补充测试，降低后续更新 Trellis 模板或平台配置时的回归风险。

## Scope

- In scope:
  - 规划 `.codex/hooks.json` 注册 `SessionStart`、`UserPromptSubmit`、可选 `SubagentStart` 的目标形态。
  - 规划新增或完善 `.codex/hooks/inject-subagent-context.py`。
  - 规划更新 `.codex/config.toml` 中关于 hooks 默认启用、可信项目、`/hooks` review 的说明。
  - 规划补充 `.trellis/tests/` 或等价测试目录，覆盖 hook manifest、hook 输出、dispatch mode、agent recursion guard。
  - 保留 `.codex/agents/trellis-research.toml`、`trellis-implement.toml`、`trellis-check.toml` 的 agent-pull fallback。
  - 同步更新 `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md` 中形成的 durable 决策。
- Out of scope:
  - 不默认修改 `.trellis/scripts`。
  - 不默认启用 `codex.dispatch_mode: sub-agent`。
  - 不实现 Ralph Loop、自动重派发、或通过 `SubagentStop` 强行关闭 subagent。
  - 不复制 Claude Code 的 `PreToolUse` matcher `Task` / `Agent` 到 Codex。

## Acceptance Criteria

- AC1: Codex 默认路径仍为 `inline`，不会在普通任务中派发 `trellis-implement` / `trellis-check`。
- AC2: Codex hooks 配置使用官方事件语义：`PreToolUse` 只按工具名过滤，subagent 上下文使用 `SubagentStart`。
- AC3: `SubagentStop` 不默认注册；如未来添加，只能用于日志或轻量校验，不做自动关闭或重试。
- AC4: `SubagentStart` 对 `trellis-research|trellis-implement|trellis-check` 生效，并能提供 active task、任务 artifacts、JSONL manifest、recursion guard 等上下文。
- AC5: 子代理在缺少 hook 注入时仍能通过 agent-pull fallback 读取 `task.py current --source`、`prd.md`、`design.md`、`implement.md`、`implement.jsonl` / `check.jsonl`。
- AC6: 测试能在本地验证 hook JSON 结构、hook 脚本输出形态、dispatch mode 行为和 agent recursion guard。

## Constraints

- Codex hooks 默认启用，但项目级 `.codex/` hooks 仍依赖项目 trusted 状态和 `/hooks` review。
- `codex.dispatch_mode` 是 Trellis/Codex 本地约定，不是 OpenAI Codex 官方配置键。
- Codex subagents 会产生额外 token 和执行复杂度，只在用户显式选择 `sub-agent` 时使用。
- 当前活动 workflow-state 是 Codex inline，实施时不得违反 “Do not dispatch implement/check sub-agents in inline mode”。

