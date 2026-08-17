# Current Contract - Trellis Codex Hooks And Subagents

## Background

- 项目已实现 Trellis/Codex 集成：`.codex/hooks.json` 注册工作流状态、子代理上下文和停止质量门禁；`.codex/hooks/*.py` 与 `.codex/agents/*.toml` 提供对应行为。
- `.trellis/config.yaml` 与 `.codex/hooks/inject-workflow-state.py` 约定 `codex.dispatch_mode` 缺失时默认 `auto`；`inline` 是主会话直接实施/检查的显式退出模式，旧值 `sub-agent` 等同于 `auto`。
- 本文保留当时的设计理由和验收边界，作为当前契约和后续回归检查的依据，不再是待实施方案。

## Current Goals

- 保持 Codex hooks 与 Claude Code hooks 的事件语义分离，避免把 Claude 的 `PreToolUse(Task/Agent)` 直接迁移到 Codex。
- 在 `auto` 模式下，让 `SubagentStart` 为 Trellis 子代理提供任务上下文，并保留子代理自行加载任务上下文的后备路径。
- 在 `inline` 模式下，由主会话直接实施和检查，不派发 implement/check 子代理。
- 保持 hooks、agent 配置和调度语义可验证，避免 Trellis 模板或平台配置更新后静默漂移。

## Current Scope

- `.codex/hooks.json` 当前注册 `UserPromptSubmit`、`SubagentStart` 和 `Stop`；`SubagentStop` 未默认注册。
- `.codex/hooks/inject-subagent-context.py` 解析原生 `SubagentStart` 输入，为受支持的 Trellis 子代理注入 active task、任务 artifacts 和 JSONL 清单上下文。
- `.codex/agents/trellis-research.toml`、`trellis-implement.toml`、`trellis-check.toml` 保留子代理角色和 child-side context fallback。
- `docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md` 记录同一份可复用结论。

## Out Of Scope

- 不修改 `.trellis/scripts`，除非独立任务证明现有接口无法支持该集成。
- 不通过 `SubagentStop` 自动关闭、重试或重派发子代理。
- 不将 Claude Code 的 `PreToolUse` matcher `Task` / `Agent` 复制到 Codex。

## Acceptance Criteria

- AC1: 缺失 `codex.dispatch_mode` 时使用 `auto`；`sub-agent` 仍解析为 `auto`；无效显式值安全回退到 `inline`。
- AC2: `PreToolUse` 仅按工具名过滤；Trellis 子代理上下文由 `SubagentStart` 处理。
- AC3: `SubagentStop` 不默认注册；如未来添加，只能用于日志或轻量校验，不做生命周期控制。
- AC4: `SubagentStart` 仅为 `trellis-research`、`trellis-implement`、`trellis-check` 提供上下文，且子代理不会递归派发 implement/check 角色。
- AC5: native context injection 不可用时，子代理仍可从 active task、任务 artifacts 和 JSONL manifests 读取所需上下文。

## Constraints

- 项目级 `.codex/` hooks 依赖项目 trusted 状态和 `/hooks` review。
- `codex.dispatch_mode` 是 Trellis/Codex 本地约定，不是 OpenAI Codex 官方配置键。
- `auto` 模式下子代理会消耗额外 token 和调度时间；上下文注入受 `.trellis/config.yaml` 中的大小限制约束。
