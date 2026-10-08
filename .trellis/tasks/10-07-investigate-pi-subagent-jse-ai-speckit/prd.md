# 调查 JSE_AI_Speckit 的 Pi subagent 实现并验证现有功能

## Goal

为当前维护者提供一份可复核的结论：说明 `D:/Workspace/JSE_AI_Speckit` 当前 Pi subagent 的实现边界、调用链、配置来源和失败回退语义，并用静态检查、单元测试和最小运行验证确认现有 subagent 是否可用。

## Background And Constraints

- 目标目录当前不是 Git 工作树，不能通过提交记录确认“最新提交”；调查以当前磁盘内容、文件修改时间、代码中的变更时间注释和现有测试为证据。
- 调查目标是只读分析与验证，不修改 `JSE_AI_Speckit` 的代码、配置、依赖或运行时台账。
- 当前任务所在仓库只保存调查计划和研究结果；不把目标仓库的实现迁移到当前仓库。
- 运行验证必须显式区分：代码/测试通过、运行环境不可用、模型或项目授权缺失、以及真实 subagent 执行失败。

## Confirmed Facts

- `.pi/settings.json` 加载 `./extensions/trellis/index.ts`，因此 Pi extension 是入口。
- `.pi/extensions/trellis/index.ts` 注册 `trellis_subagent`，支持 `single`、`parallel`、`chain` 三种 native Pi 调度模式。
- native 路径通过定位 Pi CLI，使用 `--mode json -p --no-session` 启动子进程，解析 JSON 事件并汇总文本、思考、工具调用、usage、失败分类和进度卡片。
- 单次 Trellis 角色 dispatch 会优先尝试 Herdr Pane；Herdr 不可用时才允许 native fallback。并行/链式调度保留 native 路径。
- `.pi/extensions/trellis/herdr_transport.ts` 提供 Herdr CLI/server/integration 检测、Pane 创建、等待、追加 prompt、关闭及 Pane 台账能力。
- `.trellis/config.yaml` 当前启用 Herdr，按 `preflight`、`research`、`builder`、`reviewer` 配置 platform/model/thinking；同时配置 native Pi 子代理超时和只读重试策略。
- `.trellis/tests` 与 `.pi/extensions/trellis/herdr_transport.test.ts` 提供协议、配置优先级、Pane 生命周期、超时、阻塞和台账相关测试。
- 代码注释显示 2026-09-02 起 Pane 生命周期从一次 `trellis_subagent` 调用中拆出，改由 `trellis_herdr_open/wait/send/close` 管理；2026-09-10 又强化了角色配置缺失/非法时禁止 native 或 inherited fallback 的语义。

## Requirements

### R1. Architecture explanation

Trace the end-to-end path from Pi tool invocation to either native child Pi process or Herdr Pane, including prompt construction, active-task context, role definition, model/thinking resolution, output collection, and failure reporting.

### R2. Latest-change analysis

Identify the current Pane lifecycle split, role configuration precedence, project-trust behavior, policy bridge, retry behavior, and reviewer-specific restrictions. State evidence and avoid presenting inferred behavior as confirmed behavior.

### R3. Functional verification

Run the target project's declared TypeScript check and Herdr transport test suite, run relevant Python Trellis tests, inspect the active runtime prerequisites, and execute a minimal real native Pi subagent probe when the local environment permits.

### R4. Evidence and diagnosis

Record exact commands, exit codes, relevant output, and environment blockers. A successful test suite alone is not sufficient to claim that a real subagent invocation works; the report must separate mocked transport coverage from live dispatch coverage.

### R5. Non-invasive scope

Do not alter target files or start/stop unrelated project services. Any temporary probe artifacts must be created outside the target repository or removed before completion.

## Acceptance Criteria

- [ ] A research report identifies the extension entrypoint, registered tools, native dispatch path, Herdr dispatch path, configuration/policy sources, and task-context injection behavior with file and line references.
- [ ] The report explains the 2026-09-02/2026-09-10 lifecycle and fallback changes and calls out the absence of Git history in the target directory.
- [ ] `npm run typecheck` and `npm run test:herdr` are executed in `D:/Workspace/JSE_AI_Speckit`, with results recorded.
- [ ] Relevant `.trellis/tests` Python tests are executed, with results recorded separately from TypeScript tests.
- [ ] A live native or Herdr smoke probe is executed if prerequisites are present; if not, the exact blocker and the strongest available static/mock evidence are recorded.
- [ ] The final conclusion uses one of `正常`, `部分正常`, or `无法验证`, with the reasons and remaining risks stated.
- [ ] The target repository remains unchanged after verification.

## Out Of Scope

- Modifying the target implementation, agent definitions, `.trellis/config.yaml`, or dependencies.
- Repairing Pi, Herdr, model credentials, project trust, or external provider configuration.
- Benchmarking model quality or comparing providers.
- Migrating the implementation into `full-stack-fastapi-template`.

## Open Questions

None blocking planning. Live verification outcome depends on the current machine's Pi CLI, Herdr server, platform trust, and model authentication state; these are verification results, not product decisions.
