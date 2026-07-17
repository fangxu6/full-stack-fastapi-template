# 库存只读 AI 试点实施计划

## 前置条件

- 本 PRD 与 `design.md` 已经用户评审；在得到单独的实施批准前，不运行 `task.py start`。
- 已由业务方批准：仅超级管理员、真实生产库存数据可发往 OpenAI API、30 题/90%/100% 禁止行为/P95 10 秒的门槛。
- 在任何代码或依赖变更前，重新读取相关 `.trellis/spec/backend/*`、`.trellis/spec/frontend/*`、跨层思考指南以及当时有效的 Mastra/OpenAI 官方文档。

## 子任务执行归属

本文件保留跨层顺序、验证与回滚参考；实际代码只能在下列子任务中实施：

| 顺序 | 任务 | 负责交付 | 可并行性 |
| --- | --- | --- | --- |
| 1 | `07-16-ai-backend-security-boundary` | 公共 BFF、内部工具契约、超级管理员授权与审计 | 与 sidecar 骨架可并行 |
| 2 | `07-16-mastra-inventory-orchestrator` | Mastra/OpenAI sidecar、固定工具与容器隔离 | 联调依赖后端 internal tools |
| 3 | `07-16-ai-inventory-superadmin-frontend` | 超级管理员 UI 与生成客户端接入 | API 合同稳定后开始实际接入 |
| 4 | `07-16-ai-inventory-evaluation-operations` | 题库、质量门槛、feature flag 与回滚演练 | 题库可并行；最终验收依赖全链路 |

父任务在四项完成后只执行集成验收，不应被 `task.py start` 用作直接实现目标。

## 跨层交付顺序参考

以下步骤映射到上述子任务，用于保证依赖顺序；它们不是父任务的直接执行授权。

1. **冻结外部契约与配置**
   - 选择并锁定首轮 Mastra 与 OpenAI SDK/适配器版本、具体模型快照、Responses/存储选项以及 OpenAI 项目数据控制状态。
   - 增加仅服务端使用的环境变量和部署密钥注入；不在前端、OpenAPI 示例或日志中暴露 `OPENAI_API_KEY`、internal service secret 或 actor grant。
   - 为 OpenAI 的 `X-Client-Request-Id`、供应商请求 ID、模型和成本元数据定义审计字段。

2. **建立后端 AI 边界与持久化审计**
   - 在 `backend/app` 的明确模块边界内创建 AI application/service、schemas 和 ORM migration；不把 AI 逻辑塞入现有 inventory router。
   - 创建 `ai_` 前缀的 run 与 tool-call 审计模型/DTO、索引、约束和 migration 描述，保留最小元数据和来源摘要，不复制完整生产库存 payload 或凭据。
   - 实现超级管理员依赖、输入长度限制、统一应用错误和 `request_id` 关联。
   - 为新 public API 定义 OpenAPI-visible request/response schemas。

3. **建立内部只读工具契约**
   - 创建仅 Docker 内网可访问的 internal AI tool endpoints，验证服务凭据和短时、单次 actor grant。
   - 针对余额、单据、台账和单位查询定义强类型 schema、明确字段白名单、分页/结果上限与来源摘要。
   - 复用 inventory service 的查询能力；禁止从 sidecar 直接执行 SQL，也不包装任何 mutation service。
   - 为 grant 伪造、过期、scope 不匹配、未知工具、参数越界和写入诱导分别添加测试。

4. **实现 Mastra sidecar**
   - 新建独立 TypeScript 服务、Dockerfile、健康检查和仅内部网络的 compose service；不配置 Traefik router。
   - 注册一个有界 workflow 和固定 inventory read tools；设置工具调用上限、超时及结构化输出 schema。
   - 使用 OpenAI API 的服务端项目凭据；不启用 MCP、文件、向量库、网络工具、记忆或多 Agent。
   - 透传关联 ID，记录 OpenAI 请求 ID、模型、延迟与可获取的使用量；将供应商失败映射为内部结构化失败结果。

5. **接入 FastAPI BFF 与错误流**
   - 实现 `POST /api/v1/ai/inventory/query`：认证/超级管理员校验 → run 创建 → sidecar 调用 → 审计收尾 → 结构化响应。
   - 按现有统一异常约定处理认证、验证、sidecar 超时、限流和供应商失败；所有客户端错误保留 `detail` 与 `request_id`。
   - 重新生成 OpenAPI 客户端；不手改 `frontend/src/client/**`。

6. **接入前端超级管理员入口**
   - 在 `platform/ai` 添加页面、API consumer 和薄路由；在现有菜单和路由保护中仅向超级管理员开放。
   - 显示加载、可回答、无数据、拒绝、超时和系统失败状态；每个完成回答显示来源摘要与 `request_id`。
   - 使用现有 TanStack Query/Mutation 和生成客户端；不将供应商密钥或 raw grant 放入浏览器。

7. **构建评测与运维保护**
   - 创建 30 题版本化基准和人工期望/来源判定；覆盖余额、单据、台账、空结果、边界筛选、提示注入、越权与写入请求。
   - 建立结果汇总：正确率、来源覆盖、禁止行为阻断率、P95 时延与每次调用成本。
   - 为 key 缺失、sidecar 不健康、OpenAI 限流/超时、数据留存配置未核对提供 fail-closed 行为与部署检查。

## 验证计划

### 静态与单元验证

- 后端：在 `backend/` 工作目录运行 `bash scripts/lint.sh`；仅当 `POSTGRES_DB` 已确认是 `_test` 或 `_pytest` 隔离库时运行 pytest。
- 前端：运行 `bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true ./`（不使用会写文件的 `bun run lint` 作为只读检查），再运行 `bun run build`。
- sidecar：运行其 type-check、lint、单元测试与未注册工具/无密钥启动失败测试。

### 跨层与安全验证

- 非登录用户、普通用户、停用用户均不能调用 public AI endpoint；超级管理员可调用。
- 任意请求均不能触发库存的 `POST`、`PUT`、`DELETE` 或 restore 行为；审计中无 mutation tool。
- sidecar 不能通过公网访问；浏览器网络请求中没有 OpenAI 域名、API key、internal secret 或 grant。
- 每个完成 run 均可从本地 `request_id` 关联到 run、tool call、OpenAI client/request ID 和来源摘要。
- 供应商超时、限流、空结果和无效筛选均返回可理解的失败/无数据结果，不伪造答案。

### 业务验收

- 对 30 题基准执行固定模型版本评测；至少 27 题（90%）正确且可追溯来源。
- 所有禁止行为测试均被阻止；P95 响应不超过 10 秒。
- 输出首轮调用成本报告；不将无硬预算理解为无需记录成本。

## 交付与回滚

- 首次部署前仅对超级管理员启用 feature flag，并验证 OpenAI 项目数据控制、密钥范围、网络隔离、审计与健康检查。
- 停止条件：禁止行为未被阻断、生产数据超出白名单外发、来源无法追溯、评测不达门槛、或供应商留存配置与 PRD 不一致。
- 回滚顺序：关闭 feature flag/菜单和 BFF 路由 → 停止 sidecar → 撤销 OpenAI 项目密钥与 internal secret → 保留本地审计用于调查。现有库存 API、数据库数据和页面不应回滚。

## 不在本计划中的工作

本计划不包含真正的依赖安装、代码改动、数据库迁移、供应商账户创建、生产密钥配置或部署。每项开始前均需用户批准 `task.py start`，并在执行阶段遵循相应 Trellis 规范和质量检查。
