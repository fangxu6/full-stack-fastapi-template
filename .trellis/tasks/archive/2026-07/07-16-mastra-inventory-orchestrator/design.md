# Mastra 库存 Sidecar 输出协议设计

## 边界

sidecar 是私有 Docker 服务，不连接 PostgreSQL、不接收浏览器 JWT、不配置 Traefik。
FastAPI 是唯一的公网、授权、审计与库存数据边界。sidecar 只使用 OpenAI
Responses API、固定 inventory read tools 和 FastAPI 签发的 actor grant。

## BFF 协议

`POST /v1/inventory/query`

请求 header：`X-AI-Orchestrator-Token`（FastAPI→sidecar 独立凭据）、
`X-Request-ID`、`X-AI-Actor-Grant`。请求 body：`run_id`、`question`。
`run_id` 为 UUID，`question` 经过 trim 后必须非空且最多 2,000 个字符；请求体拒绝
未知字段。

成功响应：

```json
{"status":"completed","answer":"…","citations":[{"tool_name":"balances","source":"inventory:balances","summary":"…"}],"provider_metadata":{"model":"gpt-5.6-luna","openai_request_id":"…","latency_ms":1234,"input_tokens":null,"output_tokens":null}}
```

失败响应：`{"status":"failed","error":{"category":"timeout","retryable":true}}`。
允许分类仅为 `timeout`、`rate_limited`、`provider_unavailable`、`tool_rejected`、
`tool_failed`、`invalid_response`；不得返回供应商原文。

完成响应的 `answer` 必须非空且最多 8,000 个字符，`citations` 必须为 1–5 条。每条
`summary` 非空且最多 1,000 个字符，`tool_name` 仅能为 `balances`、`documents`、
`ledger`、`processing_units` 或 `receiving_units`，`source` 必须是
`inventory:<stable-source>`。所有协议对象拒绝未知字段，防止意外引入原始库存或供应商
错误字段。

## 工作流

验证 service token 和输入 → 调用固定白名单工具（最多 FastAPI grant 所允许的次数）
→ 以工具结果生成中文回答 → 输出结构化 completed/failed envelope。模型为
`gpt-5.6-luna`，`reasoning.effort=medium`。不注册 web、files、MCP、shell、
memory 或多 agent 工具。

sidecar 调 FastAPI internal tools 时使用 `AI_INTERNAL_SERVICE_TOKEN` 与原样 actor
grant；不持久化库存记录、prompt、grant 或密钥。当前 FastAPI internal request 还要求
`actor_user_id` 时，sidecar 只从 grant 的未验证 `sub` 读取 UUID 作为路由提示；FastAPI
必须验证 grant 签名并将该值与已验证 claim 比对，sidecar 不将它视为授权事实。所有
internal list query 固定 `1 <= limit <= 20`，不得提供 deleted-record 开关。BFF 总超时
30 秒；无自动重试。

失败分类优先采用明确的边界语义：FastAPI internal tool 的 401/403 映射
`tool_rejected`，其他非成功 internal 响应映射 `tool_failed`，其 schema/JSON
无效映射 `invalid_response`；OpenAI 的 HTTP 429 映射 `rate_limited`，超时或中止
映射 `timeout`，其余 provider/network 失败映射 `provider_unavailable`。sidecar
只返回该枚举与 `retryable`，不返回异常原文。

## 可观测性与回滚

仅记录 request/run 关联、模型、OpenAI request ID、时延、可得 token 用量、错误类别
和 citation 摘要。关闭 feature flag、停止 sidecar、撤销两个 service token 与 OpenAI
项目密钥可回滚，不影响库存 API。

当前 Mastra `@mastra/core@1.51.0` 的发布声明会让 TypeScript 同时解析不兼容的 AI SDK
兼容层；sidecar `tsconfig` 因此仅对第三方声明启用 `skipLibCheck`。项目源码仍启用 strict、
noUnusedLocals 与 noUnusedParameters，且所有 sidecar 源文件继续纳入 typecheck。升级
Mastra 时必须先移除此豁免并验证完整声明检查。
