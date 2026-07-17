# AI 后端安全边界与库存工具

## 目标

实现库存只读 AI 试点的 FastAPI 业务主权边界：只允许超级管理员发起查询，持久化最小审计信息，并向私有 sidecar 提供受签名授权保护的库存只读工具面。

## 依赖与估算

- 前置：父任务 `07-16-mastra-ai-orchestration-feasibility` 的 PRD/design 契约已批准。
- 与 `07-16-mastra-inventory-orchestrator` 共享 internal tool schema；可并行开发，联调依赖本任务的 internal endpoint。
- 估算：5–7 人日。

## 范围

- 超级管理员 public AI BFF、输入/输出 schemas、统一错误与 `request_id`。
- `ai_run` / `ai_tool_call` 最小审计模型及 migration。
- 本任务新增的所有数据库对象均使用 `ai_` 前缀：表、显式索引、约束、序列和 migration 描述；不得重命名既有 inventory 或 user 数据库对象。
- 短时、run 绑定、固定调用额度的 actor grant 与 internal service authentication。
- 白名单库存余额、单据、台账、单位查询的 internal DTO 工具；参数与结果量限制、来源摘要。
- 授权、越权、grant、输入、工具和错误路径测试。

## 不在范围

- Mastra、OpenAI 调用、TypeScript 服务、前端页面或评测控制台。
- 任何库存写入工具、直接 SQL、普通用户授权或泛化 RBAC。

## 验收标准

- [ ] 非登录、普通、停用用户均无法调用 public AI BFF；超级管理员权限在服务端强制执行。
- [ ] sidecar 只能通过有效的、过期可拒绝、scope 受限的 grant 访问 internal read tools。
- [ ] 不存在任何 inventory `POST`、`PUT`、`DELETE` 或 restore 工具路径。
- [ ] 审计可由 `request_id` 关联 run、用户、工具、参数摘要和结果状态，且不保存密钥或完整敏感 payload。
- [ ] 新 public contract 使用 OpenAPI schemas，并保留现有统一 `{ detail, request_id }` 错误结构。
