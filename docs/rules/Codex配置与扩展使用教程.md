# Codex 配置与扩展使用教程（本项目）

本教程面向项目维护者和开发者，说明如何在当前仓库理解和使用 Codex 的配置、Hooks、Subagents 和 Rules。

如果你只是想让 Codex 临时按某个要求做事，直接在当前对话里说清楚即可。只有当规则需要长期保留、自动执行、约束命令，或复用到多个任务时，才需要改配置或新增扩展。

## 1. 先判断该用哪个位置

| 你想做什么 | 推荐位置 | 说明 |
| --- | --- | --- |
| 临时要求本轮任务怎么做 | 当前 prompt | 一次性约束，不写入仓库 |
| 保存仓库长期协作规范 | `AGENTS.md` | 例如开发流程、验证命令、审查重点 |
| 配置 Codex 运行参数 | `.codex/config.toml` 或用户级 `~/.codex/config.toml` | 仓库级配置只放适合随项目共享的设置 |
| 在生命周期事件中自动执行脚本 | `.codex/hooks.json` 或 `.codex/config.toml` 的 `[hooks]` | 例如会话开始、工具调用前后、提交 prompt 前注入上下文 |
| 定义专门角色的子代理 | `.codex/agents/*.toml` | 只在需要显式并行或隔离工作时使用 |
| 控制哪些命令可在沙箱外运行 | `.codex/rules/*.rules` 或用户级 rules | 例如允许、提示或禁止某类命令 |
| 可复用的任务流程 | skill | 例如 `kb-ingest`、`trellis-check` 这类操作流程 |

本项目的默认原则是：能用 prompt 解决的不要写配置，能用 `AGENTS.md` 表达的不要写 hook，能 inline 完成的不要默认派发 subagent。

## 2. 配置文件怎么放

Codex 有多层配置：

- 用户级配置：`~/.codex/config.toml`
- 用户级 profile：`~/.codex/<profile>.config.toml`
- 项目级配置：仓库内的 `.codex/config.toml`

项目级 `.codex/config.toml` 只在项目被 Codex 信任后加载。适合放这里的内容包括：

- 本仓库默认模型或推理强度
- 本仓库可用的 MCP server
- 本仓库 subagent 全局设置
- 本仓库 hooks 配置说明
- 本仓库 skill 启用策略

不要把这些内容放进项目级 `.codex/config.toml`：

- API Key 或认证信息
- 私人的模型代理地址、OpenAI base URL
- 个人通知命令
- 个人 telemetry/OTel 设置
- 个人 profile 选择

这些应该留在用户级 `~/.codex/config.toml`，因为它们属于机器或个人环境，不属于仓库。

## 3. 本项目推荐的 Codex 工作模式

当前仓库和 Trellis 的默认 Codex 模式是 `inline`：

```text
主 Codex 会话直接读取任务、规范和上下文，然后自己实施和检查。
```

也就是说，普通开发任务不要默认派发 `trellis-implement` 或 `trellis-check` 子代理。

只有当你明确需要并行、隔离上下文，或者让不同角色分别处理研究、实现、检查时，才考虑 `sub-agent` 模式。即使启用 subagent，也应该由用户明确要求，不能让配置悄悄改变默认行为。

## 4. Hooks 怎么用

Hooks 适合做“确定性、可重复”的生命周期动作。常见场景：

- 会话开始时注入项目概览
- 用户提交 prompt 前补充 Trellis workflow-state
- 工具调用前检查危险命令或生成文件修改
- 工具调用后检查输出或补充审查提示
- 子代理启动时注入任务上下文

Codex hooks 可以写在：

- `.codex/hooks.json`
- `.codex/config.toml` 的 `[hooks]`

本项目建议优先使用 `.codex/hooks.json`，避免同一层同时存在两种 hook 写法导致重复加载或启动警告。

### 常见事件怎么选

| 事件 | 适合做什么 | 注意事项 |
| --- | --- | --- |
| `SessionStart` | 会话启动、恢复、清空或压缩后注入上下文 | matcher 匹配 `startup`、`resume`、`clear`、`compact` |
| `UserPromptSubmit` | 每轮 prompt 提交前补充工作流提示 | Codex 当前忽略这个事件的 matcher |
| `PreToolUse` | 工具调用前做 guardrail | matcher 匹配工具名，如 `Bash`、`apply_patch`、MCP 工具 |
| `PermissionRequest` | Codex 准备请求权限时自动允许或拒绝 | 不会运行在无需权限的命令上 |
| `PostToolUse` | 工具调用后检查结果 | 不能撤销已经发生的副作用 |
| `SubagentStart` | 子代理启动时注入上下文 | matcher 匹配 subagent 类型 |
| `SubagentStop` | 子代理停止后做轻量观察或校验 | 不要把它当作默认关闭机制 |
| `Stop` | 回合结束时要求 Codex 再继续一轮 | 谨慎使用，避免无限继续 |

### 本项目的 Trellis/Codex 建议

- 给主会话注入 Trellis 概览，可以用 `SessionStart`。
- 给每轮任务注入 workflow-state，可以用 `UserPromptSubmit`。
- 给 Trellis 子代理注入任务上下文，应该用 `SubagentStart`。
- 不要用 `PreToolUse(Task/Agent)` 这种 Claude Code 思路迁移到 Codex。Codex 的 `PreToolUse` 匹配的是工具名，不是代理类型。
- 不要默认注册 `SubagentStop` 来自动关闭、重试或重派发子代理。

### Hook 安全注意

项目级 hooks 需要满足两个条件才会运行：

1. 项目 `.codex/` 层已被 Codex 信任。
2. 非托管 hook 已在 Codex 的 `/hooks` 界面中 review 并 trust。

如果 hook 没生效，先检查这两点，而不是马上改脚本。

## 5. Subagents 怎么用

Subagent 适合复杂且可以并行的任务，例如：

- 一个代理读代码路径，一个代理查文档，一个代理做审查
- 多个独立模块需要分别分析
- 想让某个角色保持只读，避免污染主会话上下文

不适合用 subagent 的情况：

- 小范围改动
- 用户没有明确要求并行或派发代理
- 当前任务需要连续上下文、快速迭代
- token 成本和等待时间比收益更高

自定义代理文件放在：

```text
.codex/agents/<agent-name>.toml
```

每个自定义代理至少需要：

```toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
developer_instructions = """
Review code like an owner.
Lead with concrete findings and cite files.
"""
```

可以按需要增加：

- `model`
- `model_reasoning_effort`
- `sandbox_mode`
- `nickname_candidates`
- `mcp_servers`
- `skills.config`

本项目已有 Trellis subagent 规划时，要保留三个边界：

- `trellis-research` 偏只读研究，不做代码实现。
- `trellis-implement` 负责实现，但不再派发 implement/check 子代理。
- `trellis-check` 负责检查和小修，但不再派发 implement/check 子代理。

## 6. Rules 怎么用

Rules 用来控制 Codex 在沙箱外运行命令时的策略。它不适合表达代码风格，也不适合代替 hooks。

项目级 rules 通常放在：

```text
.codex/rules/default.rules
```

示例：

```python
prefix_rule(
    pattern = ["gh", "pr", "view"],
    decision = "prompt",
    justification = "查看 PR 可以执行，但需要确认目标仓库和参数。",
    match = [
        "gh pr view 123",
        "gh pr view --repo owner/repo",
    ],
    not_match = [
        "gh pr --repo owner/repo view 123",
    ],
)
```

`decision` 有三种：

- `allow`：匹配后允许在沙箱外运行
- `prompt`：匹配后每次询问
- `forbidden`：匹配后禁止运行

如果多条规则同时匹配，Codex 使用最严格的结果：

```text
forbidden > prompt > allow
```

写 rules 时建议总是提供 `match` 和 `not_match`。这相当于规则的内联测试，能在 Codex 加载 rules 时提前发现匹配错误。

## 7. 日常维护流程

### 修改 AGENTS.md

适用场景：仓库长期协作规则变化。

1. 更新 `AGENTS.md`。
2. 确认规则不是只适用于某个临时任务。
3. 如影响开发规范，同步检查 `.trellis/spec/**`。

### 修改 Codex config

适用场景：运行参数、MCP、subagent 全局设置变化。

1. 判断是用户级还是项目级配置。
2. 项目级只放可共享、非私密、非机器绑定的配置。
3. 修改 `.codex/config.toml`。
4. 重启或新开 Codex 会话验证。

### 修改 hooks

适用场景：需要生命周期自动化。

1. 优先修改 `.codex/hooks.json` 和 `.codex/hooks/*.py`。
2. 确认事件和 matcher 语义正确。
3. 确认脚本输出符合 Codex hook JSON 约定。
4. 在 `/hooks` 中 review 并 trust。
5. 用一个小任务验证 hook 是否真的触发。

### 修改 subagents

适用场景：需要专门角色、隔离上下文或显式并行。

1. 修改 `.codex/agents/*.toml`。
2. 保持 `description` 清楚，方便 Codex 判断何时使用。
3. 给高风险角色设置更保守的 `sandbox_mode`。
4. 不要让 Trellis implement/check 子代理继续派发 implement/check。

### 修改 rules

适用场景：约束沙箱外命令。

1. 修改 `.codex/rules/*.rules` 或用户级 rules。
2. 给每条规则补 `justification`。
3. 补 `match` 和 `not_match`。
4. 重启 Codex。
5. 用 `codex execpolicy check` 验证规则。

## 8. 常见问题

### 8.1 为什么项目 hooks 没有运行？

优先检查：

- 项目是否已被 Codex 信任
- `/hooks` 里是否 review 并 trust 了该 hook
- hook 事件名是否写对
- matcher 是否匹配当前事件的字段
- hook 命令是否能从当前工作目录正常运行

### 8.2 为什么 `PreToolUse` 没有拦住某些行为？

`PreToolUse` 是工具调用 guardrail，不是完整安全边界。它主要覆盖 `Bash`、`apply_patch` 和 MCP 工具等支持的路径。某些等价操作可能通过其他工具路径发生，所以关键安全策略仍应结合 sandbox、approval policy、rules 和人工 review。

### 8.3 为什么不用 `SubagentStop` 自动关闭子代理？

Codex 本身负责等待、收集和关闭子代理结果。`SubagentStop` 更适合做观察、记录或有限校验。把它当作自动关闭、自动重试或自动重派发机制，会让流程变得难以预测。

### 8.4 什么时候应该启用 subagent？

当任务确实可以拆成独立角色并行处理，且你愿意接受额外 token、等待时间和调度复杂度时，再启用。普通 Trellis 开发任务默认走 inline。

### 8.5 Rules 和 Hooks 有什么区别？

Rules 解决“这个命令能不能在沙箱外运行”的问题。Hooks 解决“在某个生命周期点自动执行脚本或注入上下文”的问题。不要用 rules 写工作流，也不要只靠 hook 约束所有命令权限。

## 9. 提交前检查清单

- [ ] 这条规则真的需要长期保存，而不是写在 prompt 里即可。
- [ ] 选用的配置面足够小：prompt、`AGENTS.md`、config、hook、subagent、rules 没有混用。
- [ ] 项目级配置没有包含个人密钥、代理地址、通知命令或 telemetry。
- [ ] Hooks 的事件和 matcher 语义符合 Codex 官方行为。
- [ ] Subagent 仍是显式使用，不改变本项目默认 inline 工作流。
- [ ] Rules 有 `justification`、`match` 和 `not_match`。
- [ ] 更新后已经重启或新开会话，并完成必要的 `/hooks` review。

## 10. 参考资料

- AI 可检索摘要：`docs/llm-wiki/sources/codex-official-configuration.md`
- Codex 实体页：`docs/llm-wiki/entities/codex.md`
- Trellis/Codex hooks 决策：`docs/llm-wiki/queries/trellis-codex-hooks-and-dispatch-mode.md`
- 后续实施方案：`docs/specs/trellis-codex-hooks-subagents/`
- 官方原始资料本地剪藏：`docs/llm-wiki/sources/codex/`
