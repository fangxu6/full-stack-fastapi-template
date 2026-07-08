# 项目规划文档

- `docs/3-month-roadmap.md`：3 个月路线图（按双周迭代），包含每期目标、验收标准、风险点、资源配置。
- `docs/feishu-epic-story-task.csv`：可直接导入飞书项目的 `Epic -> Story -> Task` 清单，包含优先级、预估工时、负责人模板、验收标准。
- `docs/specs/trellis-codex-hooks-subagents/`：Trellis/Codex hooks 与 subagent 后续落地实施方案，记录默认 inline、显式 sub-agent、`SubagentStart`/`SubagentStop` 边界和测试计划。
- `docs/rules/Codex使用教程.md`：面向维护者的 Codex 日常使用总览，覆盖 App、CLI、IDE、Worktree、Automation、Review、MCP、Skills、Plugins、安全权限等场景。
- `docs/rules/Codex配置与扩展使用教程.md`：面向维护者的 Codex 配置、Hooks、Subagents、Rules 使用教程，说明本项目该把规则放在哪里、何时使用 subagent、如何排查 hooks。
- `docs/rules/AI编码工作流.md`：把 AI coding 调研结论落到本仓库的日常开发流程，强调短 leash、Trellis、CodeGraph、规范上下文和验证门禁。
- `docs/upstream-master-merge-2026-07-08.md`：记录 2026-07-08 合并官方 `fastapi/full-stack-fastapi-template` master 的更新范围、冲突处理和验证结果。

建议导入飞书时先映射字段，再按 `外部ID` 与 `父级外部ID` 关联父子层级。
