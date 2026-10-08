# 对齐本仓库 Pi / Codex subagent 的角色模型

## 更正说明

本任务最初被误认为针对 `D:/Workspace/JSE_AI_Speckit`（那次改动记录在 `research/alignment-report.md`）。用户澄清目标应为**本仓库** `D:/Workspace/full-stack-fastapi-template`。本文件已按正确目标重写；任务目录已从 `10-08-align-jse-pi-subagent-models` 重命名为 `10-08-align-pi-subagent-models`。

## Goal

把本仓库 Pi 与 Codex 两侧的 Trellis subagent 角色模型显式固定为当前可用的模型，使其不再隐式继承主会话/全局默认模型：

- Pi 侧：`cctq-codex/gpt-6-luna`（provider-qualified）
- Codex 侧：`gpt-6-luna`（裸 id，provider 由全局 `model_provider` 决定）

## Background And Constraints

- 本仓库 `.pi/agents/{trellis-implement,trellis-check,trellis-research}.md` 的 `model` 行原本是**注释**，示例为 `# model: openai/gpt-6-luna` —— 该 provider 在本机**并不存在**。照抄取消注释就会踩坑。
- 本仓库 `.codex/agents/{trellis-implement,trellis-check,trellis-research}.toml` 的 `model` 行同样被注释，示例为 `# model = "gpt-5.6-terra"`。
- 本仓库 `.trellis/config.yaml` **没有 `herdr:` 块**；`.pi/extensions/trellis/index.ts`（2139 行）**无任何 herdr 引用** → 本仓库只有 native 路径，匹配「团队成员未安装 Herdr」的现实。
- 本仓库在 `~/.pi/agent/trust.json` 与 `~/.codex/config.toml` 的 `[projects.…]` 中**都已受信任**，因此两侧都能真实验证。
- `.trellis/config.yaml:122-124` 说明：auto 模式下的 sub-agent **继承主会话模型，除非你 pin 一个**。这正是「未对齐」的根因 —— 两侧三个角色都没有 pin。

## Confirmed Facts

### Pi 侧

- 本仓库 extension 第 `681-682` 行：`const agentModel = agentCfg.model; const rawModel = inputModel ?? agentModel ?? str(inheritedModel);` —— frontmatter `model` 确实被消费。
- 第 `690-700` 行：无 `/` 前缀的裸 id 会直接抛错（防止落到无凭据 provider）。所以必须写 provider-qualified 形式。
- 本机 Pi provider 只有 `cctq-codex` / `rightapi-codex` / `deepseek`。

### Codex 侧

- Codex 的模型与 provider 是分开的：`~/.codex/config.toml:1-2` 为 `model_provider = "sub2api"`、`model = "gpt-6-luna"`。因此 agent `.toml` 里的 `model` 必须是**裸 id**，不能带 provider 前缀。
- 权威的 id 迁移表证明旧 id 已废弃：

  ```toml
  # ~/.codex/config.toml:47-50
  [notice.model_migrations]
  'gpt-5.2' = "gpt-5.4"
  "gpt-5.3-codex" = "gpt-5.4"
  "gpt-5.6-luna" = "gpt-6-luna"      # gpt-5.6-luna → gpt-6-luna
  ```

- `codex doctor` 报告当前活动模型与认证：

  ```text
  model                    gpt-6-luna · sub2api
  default model provider   sub2api
  auth is configured       (auth.json, api_key)
  ```

- `[model_providers.sub2api]` 的 `base_url = "https://www.cctq.ai/v1"` —— 与 Pi 的 `cctq-codex` **同一端点**，所以两侧 pin 到同一个模型是语义一致的。
- 本仓库三个 Codex agent 文件**没有** `thinking`/effort pin（`model_reasoning_effort` 仍为注释，继承全局 `xhigh`）。

## Requirements

### R1. 显式固定 Pi 侧三个角色模型

`.pi/agents/trellis-{implement,check,research}.md` 的 `model` 从注释改为生效的 `cctq-codex/gpt-6-luna`。

### R2. 显式固定 Codex 侧三个角色模型

`.codex/agents/trellis-{implement,check,research}.toml` 的 `model` 从注释改为生效的 `model = "gpt-6-luna"`（裸 id，不带 provider 前缀）。

### R3. 保留原有解释性注释与 effort 行

`model_reasoning_effort` 保持注释状态（继承全局），本轮只 pin 模型。

### R4. 不扩大改动面

不改动 extension 代码、不改 `.trellis/config.yaml`、不改凭据或两侧的信任配置。

### R5. 真实验证

- Pi：在本仓库真实派发一次 `trellis_subagent`。
- Codex：用 `gpt-6-luna` 真实执行一次非交互调用。

## Acceptance Criteria

- [ ] Pi 侧三个 agent 文件的 `model` 行为 `cctq-codex/gpt-6-luna`，不再被注释。
- [ ] Codex 侧三个 agent 文件的 `model` 行为 `gpt-6-luna`，不再被注释，且 TOML 可解析。
- [ ] Pi 侧真实派发 `trellis_subagent` 成功返回。
- [ ] Codex 侧真实 `codex exec` 用该模型成功返回。
- [ ] 未改动 extension 代码、`.trellis/config.yaml`、凭据。
- [ ] 记录「本仓库无 herdr 配置、只有 native 路径」这一事实。

## Out Of Scope

- thinking / `model_reasoning_effort` 档位。
- Herdr 协议与 `herdr.enabled`。
- provider 注册、凭据、信任配置。
- `D:/Workspace/JSE_AI_Speckit` 的改动（用户将手工回退；其 Codex agent 仍使用已废弃的 `gpt-5.6-luna`，属该仓库自己的问题）。

## Open Questions

- 是否需要一并 pin `model_reasoning_effort`（目前继承全局 `xhigh`）？
