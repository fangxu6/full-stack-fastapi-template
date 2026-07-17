# Mastra OpenAI 库存编排 Sidecar

## 目标

创建一个不对公网暴露的 TypeScript Mastra sidecar：仅使用 OpenAI API 和固定的库存只读工具，在有界工作流中生成可溯源回答。

## 依赖与估算

- 前置：父任务的 provider、数据外发、安全与输出契约已批准。
- 联调依赖 `07-16-ai-backend-security-boundary` 的 internal tool contract；可先以契约 mock 开发服务骨架。
- 估算：3–5 人日。

## 范围

- TypeScript 服务、Mastra 运行时、OpenAI 项目级服务端凭据和容器化健康检查。
- 单一有界 workflow、固定 schema 的 read-only tool registry、工具调用上限和结构化输出。
- internal service authentication、actor grant 透传、关联 ID、OpenAI 请求 ID/延迟/成本元数据。
- Docker 内网隔离、失败/超时/限流结构化结果和 sidecar 单元测试。

## 已确认输出协议

- sidecar 提供单一私有端点：`POST /v1/inventory/query`。
- FastAPI BFF 在 header 传递 `X-Request-ID` 与 `X-AI-Actor-Grant`；请求体仅含
  `run_id` 与受限长度的 `question`，不传浏览器 JWT、数据库凭据或工具选择指令。
- 成功响应为 `status: "completed"`，包含 `answer`、`citations` 与最小
  `provider_metadata`；失败响应为 `status: "failed"`，包含结构化
  `error.category` 与 `retryable`。BFF 不解析自然语言错误文本。
- 每条 citation 固定为 `tool_name`、`source`、`summary`；`source` 使用稳定
  internal source（如 `inventory:balances`），`summary` 只含筛选/结果数量摘要，
  不包含原始库存记录。
- `error.category` 仅为 `timeout`、`rate_limited`、`provider_unavailable`、
  `tool_rejected`、`tool_failed` 或 `invalid_response`；只有前三类可标记
  `retryable: true`。不得透传 OpenAI 原始错误文本。
- 低实时性与低出口带宽条件下，BFF → sidecar 的总超时可为 30 秒；sidecar
  内部的 OpenAI 与 internal-tool 阶段预算相应提高。首版不自动重试，避免重复
  执行受额度限制的工具调用；用户可显式重新提问。
- `provider_metadata` 只含 `model`、`openai_request_id`、`latency_ms` 及可得的
  `input_tokens` / `output_tokens`；不得包含 API key、完整供应商 headers 或原始
  OpenAI 响应。
- FastAPI → sidecar 使用独立 `AI_ORCHESTRATOR_SERVICE_TOKEN`，在
  `X-AI-Orchestrator-Token` 传递；sidecar → FastAPI internal tools 继续使用
  `AI_INTERNAL_SERVICE_TOKEN`。两个方向的 token 不可复用；actor grant 随请求
  透传。
- 首轮模型固定为 `gpt-5.6-luna`；实施使用 Responses API 的 structured outputs
  与 function calling，但 sidecar 不注册模型支持的 web/file/MCP/shell 等非白名单
  工具。部署前仍须以当前项目权限验证模型可用性。
- 首轮固定 `reasoning.effort: "medium"`；任何调整必须通过同一 30 题基准比较
  正确率、来源覆盖、P95 和成本，不能静默改变评测基线。

## 不在范围

- 直连 PostgreSQL、接收浏览器 JWT、Traefik/public router、MCP、文件、向量库、记忆、多 Agent、网络或写入工具。
- FastAPI public BFF、前端或最终业务评测。

本任务不创建数据库对象；如未来需要 sidecar 持久化，必须新建 task，并遵守父任务的 `ai_` 数据库对象前缀规则。

## 验收标准

- [ ] sidecar 没有公网 Traefik 路由，也没有数据库凭据；浏览器无法直接访问。
- [ ] 仅声明的库存 read tools 可被调用，未知工具/超限调用/无效 grant 均失败关闭。
- [ ] 每次模型调用关联本地 run/request ID、OpenAI request ID、模型、延迟和可得成本元数据。
- [ ] 缺失凭据、OpenAI 限流/超时、internal tool 失败均返回结构化失败，而不生成无来源答案。
- [ ] OpenAI key 只在服务端配置中出现，且实际端点/`store`/数据控制在部署前被核对。
