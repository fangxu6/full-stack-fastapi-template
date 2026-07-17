# 库存只读 AI 试点技术设计

## 决策

**有条件采用 Mastra，且仅用于独立的 TypeScript 编排 sidecar。**

FastAPI 继续是唯一的业务数据、认证、授权、审计与公网 API 边界；Mastra 不连接 PostgreSQL、不接收浏览器 JWT、不暴露到 Traefik，也不能调用现有库存写入端点。该设计借用 Mastra 的工作流、工具契约、模型提供方与可观测性原语，而不迁移现有业务服务到 TypeScript。

## 目标与约束

- 仅超级管理员可使用库存只读问答。
- 本父任务及全部子任务新增的数据库对象使用 `ai_` 前缀；不重命名既有业务表。
- 仅支持库存余额、库存单据与库存台账的白名单查询；禁止新增、编辑、删除、恢复、SQL、MCP、网络、文件系统及任意代码执行工具。
- 真实生产库存数据可发送到 OpenAI API，但只发送当前问题所需的最小字段集；不得外发用户 JWT、数据库/服务凭据、密钥或无关个人资料。
- 所有结果必须携带数据来源摘要；工具失败、空结果或权限失败必须显式呈现，不得由模型补全。
- 试点保持无状态：不使用长期记忆、OpenAI Conversations、Files、Vector Stores、RAG 或后台模式。

## 目标拓扑

```text
React platform/ai 页面
  │  POST /api/v1/ai/inventory/query（同源、JWT）
  ▼
FastAPI AI BFF / application service
  ├─ 校验 CurrentUser + get_current_active_superuser
  ├─ 创建 ai_run，保留 request_id
  ├─ 签发短时、单次、只读的内部 actor grant
  │
  │ 私有 Docker 网络；无 Traefik 路由
  ▼
Mastra AI orchestrator（TypeScript sidecar）
  ├─ 单一工作流：输入校验 → 有界工具调用 → 回答合成
  ├─ 仅注册 inventory_read 工具组
  ├─ OpenAI API（项目级服务端凭据）
  │
  │ 私有 Docker 网络 + actor grant
  ▼
FastAPI internal AI tool endpoints
  ├─ 验证 grant、run、过期时间和只读 scope
  └─ 调用现有 inventory service / DTO 查询
       ▼
     PostgreSQL
```

React 永远不直接访问 sidecar 或 OpenAI；sidecar 永远不直接访问数据库。`compose.yml` 现有只有 frontend、backend 与 db，因此 sidecar 是将来新增的内部服务，不改变现有公网前后端域名。

## 交付归属

本设计是父任务的共享契约，不是父任务的直接实现清单。实现责任已拆分为：

- `07-16-ai-backend-security-boundary`：FastAPI BFF、授权、审计、grant 与 internal read tools；
- `07-16-mastra-inventory-orchestrator`：TypeScript Mastra/OpenAI sidecar、工具注册与 Docker 内网；
- `07-16-ai-inventory-superadmin-frontend`：React `platform/ai`、菜单/路由和来源/失败体验；
- `07-16-ai-inventory-evaluation-operations`：30 题评测、成本/时延、安全门槛与 rollout/rollback。

父任务只在各子任务验收后执行跨层集成复核；任何实现都应从对应子任务开始，而不是启动本父任务。

## 责任边界

| 层 | 负责 | 明确不负责 |
| --- | --- | --- |
| React `platform/ai` | 超级管理员入口、提问、加载/失败状态、显示回答和来源 | 保存 OpenAI 密钥、执行数据查询、决定权限 |
| FastAPI public AI BFF | JWT 与超级管理员校验、输入限制、run/audit、统一错误与请求关联、向 sidecar 发起内部调用 | 直接拼接模型提示词、让浏览器调用外部供应商 |
| Mastra sidecar | 有界工作流、强类型工具选择、OpenAI 调用、返回结构化答案和工具轨迹 | 读取 PostgreSQL、信任浏览器身份、执行写操作 |
| FastAPI internal tools | 验证 service grant、按 DTO/服务读取白名单数据、限制参数和结果量 | 接受公网请求、返回 ORM 实体、执行库存变更 |
| OpenAI API | 根据允许的库存上下文生成回答 | 身份授权、事实来源、持久业务审计 |

## API 与数据契约（拟议）

### 公共 BFF

新增 `POST /api/v1/ai/inventory/query`。请求只含 `question`（受长度和字符集限制）与可选的客户端相关标识；不得接受任意工具名、原始 SQL、模型参数或供应商配置。响应包含：

- `run_id`、`request_id`、`status`；
- `answer` 或明确的不可回答/失败说明；
- `citations[]`：工具名、业务日期/筛选条件、返回记录摘要和可选页面跳转信息；
- 不包含 OpenAI 密钥、原始供应商 HTTP 头、内部 grant 或未脱敏审计内容。

路由使用现有 `get_current_active_superuser` 依赖。错误继续使用统一 `{ detail, request_id }` 合同；供应商不可用、超时或速率限制应映射为稳定的应用错误码/文案，而不是将模型错误透传给浏览器。

### 内部工具面

sidecar 通过 Docker 服务名调用 `/internal/ai/inventory/*` 工具端点。现有 backend host router 不按 path 隔离，因此每个端点必须先以 service credential 和 actor grant 拒绝未授权调用；Traefik path deny 或独立 internal listener 是后续部署加固，不能替代服务端校验。每个端点须：

1. 校验 FastAPI 签发的短时、run 绑定 actor grant：`run_id`、原始超级管理员 ID、允许工具 scope、签发/过期时间及调用额度；每次工具调用原子消费额度；
2. 校验强类型筛选参数与最大 `limit`，忽略或拒绝未声明字段；
3. 调用既有 inventory service，返回 schemas/DTO，而不是 SQLModel ORM 对象；
4. 写入工具审计事件并带回可展示的来源摘要。

第一版工具清单固定为 `list_balances`、`list_documents`、`list_ledger_entries`、`list_processing_units` 和 `list_receiving_units` 的只读投影。写入端点（`POST`、`PUT`、`DELETE`、`restore`）不建立工具包装，也不出现在 Mastra 注册表中。

## 工作流与回答规则

使用一个确定性外壳的 Mastra workflow，而不是开放式多 Agent 网络：

1. FastAPI 生成 run 与 grant，并将问题和关联标识交给 sidecar。
2. 工作流校验输入并最多调用有限次数的白名单工具；工具输入/输出使用 schema 验证。
3. sidecar 将工具结果和来源摘要送至 OpenAI 生成中文回答；回答只能引用工具返回的事实。
4. sidecar 返回结构化 `answer / citations / tool_trace / model_metadata`；FastAPI 记录审计并返回前端。

没有匹配项、字段不完整、工具错误或超时必须走显式结果分支。第一版不允许模型自行选择外部网络工具、MCP、子 Agent、记忆或暂停/恢复流程。

## 身份、密钥与数据保留

- 浏览器只携带现有 JWT 给 FastAPI；JWT 不跨越到 sidecar 或 OpenAI。
- OpenAI 项目级密钥只存在 sidecar 的服务端密钥配置中，不进入前端构建产物、公共 FastAPI 响应、日志或数据库。
- FastAPI 与 sidecar 使用独立的内部服务密钥以及短时 actor grant；仅依赖 Docker 内网不是授权机制。
- 请求至 OpenAI 使用可关联的 `X-Client-Request-Id`，并记录 OpenAI 返回的 `x-request-id`、模型版本、延迟和 token/成本元数据（如 SDK 可取得）。
- 采用无会话、无文件、无向量存储的请求方式；在实施时显式核对 OpenAI API 所用端点的 `store` 行为和项目级数据控制。根据官方数据控制文档，默认 API 流量仍可能有最长 30 天的滥用监控日志，不能承诺零留存；若需更严格的留存控制，必须获得 OpenAI 的项目/组织级批准后再启用。

## 审计、可观测性与评测

新增持久化 `ai_run` 和 `ai_tool_call` 记录，最少包含：本地 `request_id`、run ID、用户 ID、状态、允许工具、筛选摘要、供应商/模型、OpenAI 请求 ID、时延、token/成本、错误类别与时间戳。表、显式索引、约束、序列及 migration 描述均使用 `ai_` 前缀；生产库存字段本身不完整复制到审计表，保留可重放的参数摘要和来源标识即可。

`request_id` 是根关联键；OpenAI 的 `X-Client-Request-Id` 使用同一 run 可追溯值。Sentry/结构化日志不得记录密钥或完整提示词。运行面板与基准评测是后续实现范围，不是本 task 的交付。

评测基准为 30 个由业务方人工核验的问题，覆盖余额、单据、台账、空结果、错误筛选、越权、写入诱导和提示注入。门槛为：至少 90% 正确且有来源、禁止行为 100% 被阻止、P95 不超过 10 秒；每次调用成本必须可汇总。

## 前端放置与体验

页面放在 `frontend/src/platform/ai/pages/`，路由文件保持薄，仅挂载在现有受登录保护的 `_layout` 下，并在 `beforeLoad` 或页面数据加载阶段应用 `requireSuperuser`。菜单配置只对超级管理员呈现入口；服务端仍是决定性限制。

页面使用 TanStack Query/Mutation 调用生成的 OpenAPI 客户端。后端 public contract 变化后必须运行仓库的 client generation，不得手改 `frontend/src/client/**`。回答区显示运行状态、答案、来源摘要、`request_id` 和安全失败提示。

## 风险、兼容与回滚

| 风险 | 缓解 | 回滚 |
| --- | --- | --- |
| 模型生成不可靠 | 仅以工具结果作答、来源可见、30 题评测、无匹配即拒答 | 关闭入口和 sidecar，不影响库存页 |
| 生产数据外发 | 最小字段、项目密钥、数据保留记录、无文件/RAG | 停止 sidecar、撤销 OpenAI 项目密钥、保留本地审计 |
| 权限扩大 | FastAPI 超级管理员校验 + 单次 grant + internal endpoint 校验 | 禁用 BFF 路由和 internal grants |
| sidecar 不可用/超时 | 超时、有限重试、统一错误、无静默降级 | FastAPI 返回可追踪失败，不改变库存 API |
| 供应商/模型变化 | 供应商适配边界、固定模型版本、记录模型元数据 | 切换适配器/模型或禁用 AI 功能 |

## 延期项

写操作与人工审批、普通用户/库存域 RBAC、长期记忆、RAG、向量库、MCP、外网工具、多 Agent、异步任务及常驻对话均不在首个试点内。它们必须各自创建 task，并重新定义权限、数据保留、评测和回滚标准。

## 设计验证与后续知识沉淀

实施前需再次核对 Mastra 版本/包、OpenAI API 可用端点与项目数据控制；规划不能替代当时的官方文档确认。实现并通过质量门后，应将稳定的 AI 服务边界、授权和数据外发规则更新到 `.trellis/spec/`；如形成可跨 task 复用的事实，再使用 `kb-ingest` 更新 `docs/llm-wiki/`。
