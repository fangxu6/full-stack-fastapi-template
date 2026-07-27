# 库存 AI 超级管理员前端体验

## 目标

在 React `platform` 层提供仅超级管理员可见的库存只读问答入口，清楚展示回答来源、运行状态和可追踪失败，同时不泄漏任何外部供应商或内部服务凭据。

## 依赖与估算

- 前置：父任务的页面与安全体验契约已批准。
- 实际 API 接入依赖 `07-16-ai-backend-security-boundary` 稳定 public BFF/OpenAPI contract；页面状态可先以 mock 开发。
- 估算：2–3 人日。

## 范围

- `platform/ai` 页面、薄路由、超级管理员 route guard 和菜单可见性。
- 生成 OpenAPI client 的 query/mutation 接入、提问、答案、来源、无数据、拒绝、超时和系统失败状态。
- `request_id` 的用户可见故障关联与无敏感信息的错误展示。
- 前端单元/组件与必要的浏览器测试。

## 不在范围

- 浏览器调用 OpenAI 或 sidecar、保存 API key/grant、普通用户入口、对话记忆、库存页面重构。

本任务不创建数据库对象；前端仅通过 BFF 使用后端 `ai_` 前缀的审计/运行记录，不得引入另行命名的持久化存储。

## 验收标准

- [ ] 非超级管理员既看不到入口，也不能通过路由进入 AI 页面；服务端 403 仍正确展示。
- [ ] 页面仅调用 FastAPI public BFF，浏览器网络中不存在 OpenAI URL、API key、internal secret 或 actor grant。
- [ ] 成功答案显示来源摘要；空结果、权限拒绝、超时和系统错误均有不同且可理解的状态。
- [ ] 后端 contract 更新后通过生成客户端接入，没有手改 `frontend/src/client/**`。
- [ ] 构建、只读 Biome 检查与相关 UI 测试通过。
