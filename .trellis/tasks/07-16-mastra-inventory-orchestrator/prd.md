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

## 不在范围

- 直连 PostgreSQL、接收浏览器 JWT、Traefik/public router、MCP、文件、向量库、记忆、多 Agent、网络或写入工具。
- FastAPI public BFF、前端或最终业务评测。

## 验收标准

- [ ] sidecar 没有公网 Traefik 路由，也没有数据库凭据；浏览器无法直接访问。
- [ ] 仅声明的库存 read tools 可被调用，未知工具/超限调用/无效 grant 均失败关闭。
- [ ] 每次模型调用关联本地 run/request ID、OpenAI request ID、模型、延迟和可得成本元数据。
- [ ] 缺失凭据、OpenAI 限流/超时、internal tool 失败均返回结构化失败，而不生成无来源答案。
- [ ] OpenAI key 只在服务端配置中出现，且实际端点/`store`/数据控制在部署前被核对。
