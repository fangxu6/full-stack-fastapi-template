# Mastra 库存 Sidecar 实施计划

1. 创建独立 TypeScript 服务，锁定 Mastra/OpenAI SDK 版本；在启动时 fail closed
   验证 `OPENAI_API_KEY`、`AI_ORCHESTRATOR_SERVICE_TOKEN`、
   `AI_INTERNAL_SERVICE_TOKEN`、FastAPI internal URL 和 `OPENAI_MODEL=gpt-5.6-luna`。
2. 用 Zod/TypeScript 定义已冻结的 BFF request、completed/failed response、citation
   与 provider metadata schema；请求 question 上限 2,000 字符，完成回答上限 8,000 字符，
   citation 为 1–5 条且 summary 上限 1,000 字符；验证 inbound service token、request ID、
   actor grant。
3. 实现固定的 balances/documents/ledger/processing-units/receiving-units tool adapter；
   仅调用 FastAPI internal endpoints，透传 actor grant、request ID 和 internal token，
   固定每次 `limit <= 20`，并拒绝未知工具或与 endpoint 不符的 response envelope。
4. 实现 Responses API workflow，固定 `reasoning.effort=medium`、30 秒总预算下的阶段
   超时、无自动重试和结构化错误映射；不启用任何非白名单 OpenAI 工具。
5. 添加 `/health`、Dockerfile、compose 内部服务和无 Traefik labels；配置日志脱敏。
6. 编写 unit/contract tests：token 缺失、grant 透传、未知工具、工具失败、OpenAI 超时/
   限流、无 citation、成功 metadata；再由后端任务接入 BFF client。

验证：运行 sidecar 的 type-check、lint、unit tests；以 mock FastAPI/OpenAI 验证协议。
Docker 联调与 30 题评测留待相关任务及具备 Docker CLI 的环境。
