# Codex 使用教程（本项目）

本教程面向项目维护者和开发者，说明如何在当前仓库日常使用 Codex。它基于 OpenAI Codex 官方文档整理，覆盖官网中不只限于 config、Hooks、Subagents、Rules 的使用主题。

如果你要修改 Codex 的配置、hooks、subagents、rules，请继续看深入篇：[Codex配置与扩展使用教程.md](./Codex配置与扩展使用教程.md)。

## 1. Codex 能帮你做什么

Codex 是面向软件开发的 coding agent。它适合：

- 写代码：根据需求在现有项目结构中实现功能。
- 读代码：解释陌生模块、调用链、架构边界。
- 做 review：找 bug、行为回归、遗漏测试和安全风险。
- 调试问题：阅读日志、复现失败、定位根因、做小步修复。
- 自动化重复任务：例如测试、迁移、重构、文档整理、例行检查。

在本项目里，Codex 应优先遵循：

- 根目录 `AGENTS.md`
- `.trellis/spec/**`
- `docs/rules/**`
- `docs/specs/**`
- `docs/llm-wiki/**` 中的 AI 可检索知识

## 2. 选择使用入口

Codex 不只有一种入口。不同入口适合不同工作方式。

| 入口 | 适合场景 | 本项目建议 |
| --- | --- | --- |
| Codex App | 多线程、本地/Worktree/Cloud、内置 diff、终端、自动化 | 日常主入口，适合复杂任务和持续协作 |
| Codex CLI | 终端内快速问答、脚本化、非交互执行 | 适合一次性检查、自动化和熟悉命令行的人 |
| IDE Extension | 需要编辑器上下文、选中文件、局部代码修改 | 适合贴近代码的短任务和 review |
| Codex Web/Cloud | 远程运行、云环境、PR review、Slack/Linear/GitHub 集成 | 适合离线跑长任务或团队协作 |

本仓库在 Codex App 中使用最顺手：可以保留线程、查看 diff、开终端、用 worktree 隔离变更，也能把教程和任务上下文都留在同一个工作流里。

## 3. 提示词怎么写

官方最佳实践建议把任务说明拆成四块。你可以直接套这个格式：

```text
目标：
要完成什么功能、修复什么问题、回答什么问题。

上下文：
相关文件、目录、错误日志、设计文档、截图、复现步骤。

约束：
不能改哪些文件、必须遵守哪些规范、风险边界是什么。

完成标准：
什么测试要通过、什么行为要改变、最后需要交付什么。
```

本项目推荐的例子：

```text
目标：修复用户列表页面筛选条件刷新后丢失的问题。
上下文：前端在 frontend/src/routes/_layout/admin/users.tsx，数据请求在 frontend/src/features/users/。
约束：routes 继续保持 thin，不直接编辑 frontend/src/client/**。
完成标准：实现修复，运行相关前端 lint/build，并说明验证结果。
```

复杂任务先让 Codex 计划：

```text
先进入计划模式，读取相关代码和规范，给出实现计划。不要先改文件。
```

在 Codex App 或 CLI 中也可以用 `/plan` 进入计划模式。

## 4. 本项目的默认工作流

普通开发任务按这个顺序走：

1. 明确目标和完成标准。
2. 读取 `AGENTS.md`、`.trellis/spec/**` 和相关 `docs/specs/**`。
3. 让 Codex 搜索现有代码，确认当前实现事实。
4. 小步修改代码或文档。
5. 运行与风险匹配的检查。
6. 让 Codex 总结改动、验证结果、剩余风险。

当前 Trellis/Codex 默认是 `auto`：主会话负责协调，实施、检查和研究工作默认可派发给 `trellis-implement`、`trellis-check` 和 `trellis-research`。显式设置 `inline` 才由主会话直接实施和检查；旧值 `sub-agent` 仍兼容，但等同于 `auto`。

## 5. App 中怎么用

Codex App 适合大多数本地开发任务。

常用能力：

- 多项目和多线程：一个窗口中并行处理多个项目或任务。
- Local 模式：直接在当前 checkout 中工作。
- Worktree 模式：为任务创建独立 Git worktree，避免影响当前工作区。
- Cloud 模式：把任务交给云端环境运行。
- 内置 diff：查看改动、评论某行、阶段性确认。
- 内置终端：运行测试、查看服务输出、让 Codex 读取终端结果。
- In-app browser：预览本地 web 页面，并在页面上点选反馈。
- Automations：定期运行检查、提醒或持续跟进。

建议：

- 小改动用 Local。
- 试验性、大范围或并行任务用 Worktree。
- 想让 Codex 离线跑较长任务时用 Cloud。
- 前端 UI 任务尽量配合 in-app browser 或截图。

## 6. CLI 中怎么用

启动交互式 TUI：

```bash
codex
```

带初始提示启动：

```bash
codex "解释这个仓库的后端模块边界"
```

指定目录：

```bash
codex --cd D:/Workspace/full-stack-fastapi-template
```

非交互执行：

```bash
codex exec "检查本次 diff 是否有明显文档链接错误"
```

恢复会话：

```bash
codex resume
codex resume --last
```

本项目常用 slash commands：

- `/status`：查看线程 ID、上下文和额度状态。
- `/plan`：进入计划模式。
- `/review`：审查未提交变更、某个 commit 或与 base branch 的 diff。
- `/mcp`：查看 MCP 服务器状态。
- `/permissions`：切换权限和沙箱模式。

## 7. IDE Extension 中怎么用

IDE Extension 适合贴近代码的任务。

常用方式：

- 选中代码后让 Codex 解释或修改。
- 在 prompt 中引用文件，例如 `@example.tsx`。
- 用 Auto Context 让 Codex 读取当前编辑器上下文。
- 在本地和 Cloud 模式之间切换。
- 用 `/review` 做本地 diff review。

如果任务要跨多个文件、需要长时间执行，建议切到 Codex App 或 CLI。IDE 更适合局部、快速、上下文明确的任务。

## 8. Review 怎么用

Codex 可以做本地 review，也可以在 GitHub/Cloud 场景中做 PR review。

本地 review 适合提交前自查：

```text
/review
```

常见 review 目标：

- 未提交变更
- 某个 commit
- 当前分支相对 base branch 的 diff
- 自定义重点，比如安全、可访问性、测试遗漏

让 Codex review 时，应该要求它优先找真实风险：

```text
请以 code review 视角审查本次改动，优先找 correctness、安全、行为回归和遗漏测试。不要输出纯风格建议。
```

## 9. Worktree 怎么用

Worktree 是 Codex App 中隔离任务的关键能力。它基于 Git worktree，为同一仓库创建一个独立 checkout。

适合用 Worktree 的情况：

- 你想让 Codex 并行做一个任务，但不污染当前工作区。
- 你想试验一个方案，之后再决定是否合并。
- 自动化任务可能产生改动，需要和当前手头工作隔离。

注意：

- Worktree 只适用于 Git 仓库。
- 同一个分支不能同时被多个 worktree checkout。
- Codex 管理的 worktree 默认放在 `$CODEX_HOME/worktrees`。
- 归档线程时，Codex 可能清理对应 worktree；重要工作要及时创建分支、提交或 handoff 到 Local。

## 10. Automations 怎么用

Automations 用于定期、后台、重复执行的任务。

适合：

- 定时检查 CI、PR 状态或错误日志。
- 每天生成项目状态报告。
- 定期检查某个文档或规范是否漂移。
- 长任务完成后提醒并回到同一线程。

两种常见类型：

- Thread automation：绑定当前线程，保留上下文，适合持续跟进同一个问题。
- Standalone/project automation：每次独立运行，适合周期性检查和报告。

安全建议：

- 先在普通线程中手动跑一次 prompt，确认结果稳定。
- 优先用 Worktree 隔离 automation 产生的改动。
- 避免在 full access 下跑无人值守 automation。
- automation prompt 要写清楚“什么时候报告、什么时候归档、什么时候停止”。

## 11. 外部工具：MCP、Skills、Plugins

这三者解决不同问题：

| 能力 | 用途 | 例子 |
| --- | --- | --- |
| MCP | 连接外部工具和数据源 | GitHub、Figma、Sentry、OpenAI Docs、浏览器 |
| Skill | 封装可复用工作流 | `kb-ingest`、`trellis-check`、日报生成 |
| Plugin | 分发 skills、MCP、hooks、应用集成 | 团队共享插件、个人插件市场 |

使用顺序建议：

1. 先用 `AGENTS.md` 固化仓库约定。
2. 重复流程用 skill。
3. 需要外部系统能力时接 MCP。
4. 需要跨团队安装和共享时打包成 plugin。

本项目已经有 `.agents/skills/**`，日常应优先复用现有 skill，而不是把长流程写进 prompt。

## 12. 安全、权限和网络

Codex 安全控制主要由两层组成：

- Sandbox：技术上能读写哪里、能不能访问网络。
- Approval policy：什么时候必须问你。

常见模式：

| 模式 | 适合场景 |
| --- | --- |
| Read-only | 只读分析、规划、审查 |
| Workspace-write + on-request | 日常开发默认选择 |
| Danger/full access | 只在外部环境已隔离且你明确接受风险时使用 |

网络默认应保持谨慎。需要联网时，优先说明原因和目标域名。不要为了方便长期打开无限制网络访问。

在本项目中尤其注意：

- 不直接编辑生成文件：`frontend/src/client/**`、`frontend/src/routeTree.gen.ts`。
- 不让 Codex 随意操作仓库外文件。
- 不把 API Key、私有 token、个人代理地址写进项目配置。
- 对 destructive 命令、跨目录写入、网络访问保持人工 review。

## 13. 什么时候更新教程或规则

出现这些情况时，应更新 `AGENTS.md`、`.trellis/spec/**` 或 `docs/rules/**`：

- Codex 连续两次犯同类错误。
- review 中反复出现相同反馈。
- 某个流程开始被多次复用。
- 项目约束从“口头约定”变成“必须遵守”。
- Codex 官方行为变了，导致本地 hooks/config/rules 教程过期。

更新顺序：

1. 先确认当前代码和当前官方文档。
2. 更新人读的教程或规则。
3. 如果 AI 也需要检索，更新 `docs/llm-wiki/**`。
4. 如果是工程执行规则，检查 `.trellis/spec/**` 是否也要同步。

## 14. 快速检查清单

开始任务前：

- [ ] 我是否给了目标、上下文、约束和完成标准？
- [ ] 是否需要先 `/plan`？
- [ ] 是否已经指明相关文件、错误日志或截图？
- [ ] 是否说明了不能改的文件和生成文件边界？

让 Codex 改完后：

- [ ] 是否查看了 diff？
- [ ] 是否运行了对应测试、lint、type-check 或文档校验？
- [ ] 是否让 Codex 说明验证结果和剩余风险？
- [ ] 是否需要更新 `AGENTS.md`、`.trellis/spec/**`、`docs/rules/**` 或 `docs/llm-wiki/**`？

## 15. 参考资料

- OpenAI Codex 官网入口：https://developers.openai.com/codex
- 官方最佳实践：https://developers.openai.com/codex/learn/best-practices
- Codex App 功能：https://developers.openai.com/codex/app/features
- AGENTS.md 官方指南：https://developers.openai.com/codex/guides/agents-md
- MCP 官方指南：https://developers.openai.com/codex/mcp
- 本项目深入篇：`docs/rules/Codex配置与扩展使用教程.md`
- AI 可检索摘要：`docs/llm-wiki/sources/codex-official-configuration.md`
