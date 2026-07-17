# AI 后端安全边界与库存工具设计

## 决策

AI 是一个新的模块边界，而不是 inventory router 的附加端点：

- 持久化表置于 `backend/app/models/ai.py`，并由 `backend/app/models/__init__.py` 导入以参与 Alembic metadata；
- public/internal DTO 置于 `backend/app/schemas/ai.py`；
- orchestration、grant 与 inventory read projection 置于 `backend/app/modules/ai/service.py`；
- public BFF 与 internal tool router 置于 `backend/app/modules/ai/router.py`；
- `backend/app/api/main.py` 仅负责注册 public `/api/v1/ai` router。internal router 的注册方式与代理拒绝规则在实现时按 sidecar 部署拓扑确认。

该划分符合此能力同时拥有外部服务、跨表审计、权限、内部服务认证和跨模块查询的事实；inventory 服务继续是库存查询的唯一业务实现。

所有新增持久化数据库对象须以 `ai_` 开头：SQLModel `__tablename__` 使用 `ai_run`、`ai_tool_call`；显式索引、unique/check/foreign-key 约束和序列同样使用 `ai_`（例如 `ix_ai_run_request_id`、`uq_ai_tool_call_run_sequence`）。Alembic revision 的说明也须以 AI 前缀对象为主题；既有 `user` 和 inventory 对象不重命名。

## 安全不变量

1. public BFF 使用现有 `get_current_active_superuser`。普通、停用、匿名用户不能取得 run、grant 或任何库存投影。
2. sidecar 没有数据库凭据、用户 JWT 或库存 mutation 路径；所有库存数据均经 FastAPI service/DTO 返回。
3. public BFF 只接收受限长度的自然语言 `question`，不接收工具名、SQL、model/provider 参数、grant 或 service credential。
4. internal endpoints 即使被外部 host 命中，也必须先验证 static service credential 和短时 run-grant；Docker 内网、URL 前缀和菜单隐藏都不是授权控制。
5. 只注册 `balances`、`documents`、`ledger`、`processing_units` 与 `receiving_units` 的 read projection。现有 inventory 的 `POST`、`PUT`、`DELETE`、restore service 不被包装。
6. 所有预期拒绝使用语义 `AppError`；错误保持 `{ detail, request_id }` 与 `X-Request-ID`。

## 数据模型与审计

新增两张带仓库 audit-field contract 的表：

| 表 | 最小字段 | 不保存 |
| --- | --- | --- |
| `ai_run` | UUID id、request_id、user_id、status、question 摘要/哈希、允许 scopes、max/used tool calls、provider/model metadata、开始/结束时间、error category、created/updated/deleted audit fields | JWT、service secret、actor grant、完整 prompt、完整库存结果 |
| `ai_tool_call` | UUID id、run_id、sequence、tool_name、参数摘要、来源摘要、status、时延、错误类别、created/updated/deleted audit fields | 原始数据库记录、密钥、sidecar header |

`created_by` 和 `updated_by` 均来自发起该 run 的超级管理员。所有时间使用现有 `get_datetime_utc`。`ai_run` 的 counter 与 `ai_tool_call` 插入必须在同一数据库事务内完成，防止并发调用绕过工具上限。

## 授权与 grant 协议

### Public BFF

`POST /api/v1/ai/inventory/query`（拟议）执行：

1. 验证 `get_current_active_superuser`；
2. 验证 request schema 和问题长度；
3. 创建 `ai_run`，初始允许固定 read scopes 与 `max_tool_calls`；
4. 以独立 `AI_ACTOR_GRANT_SIGNING_KEY` 签发短时 HMAC JWT-like grant，payload 仅含 `run_id`、`user_id`、scopes、expiry、issuer/audience 和 `jti`；
5. 通过 server-to-server client 调用 sidecar；sidecar 健康、超时和网络失败映射为语义服务不可用错误；
6. 收到结构化结果后结束 run，返回 public response schema 与现有 request ID。

`AI_ENABLED` 默认 false；未启用或缺少必要配置必须 fail closed。OpenAI key 不属于此 FastAPI 子任务，也不进入 public response 或审计表。

### Internal tools

sidecar 每次工具调用同时提交 `AI_INTERNAL_SERVICE_TOKEN` 和 actor grant。FastAPI 用常量时间比较验证 service token，再验证 grant 的签名、issuer、audience、expiry、run/user/scopes。每次调用使用原子条件更新 `used_tool_calls < max_tool_calls` 取得一个 slot 并写 `ai_tool_call`；因此 grant 对一个 run 短时有效、只能执行固定数量的已授权 read calls，而不是可无限重放的 bearer token。

这是对父设计“单次 grant”的精确化：单次问答可有多个工具调用，但每次调用都必须消费不可恢复的调用额度。未知 tool、scope 不匹配、过期 grant、错误 service token 或额度用尽均返回拒绝，且不运行 inventory query。

## 库存 read projection

内部 router 不调用 SQL 或 ORM 查询细节；它调用现有 `app.modules.inventory.service` 的：

- `list_processing_units` / `list_receiving_units`；
- `list_documents`；
- `list_balances`；
- `list_ledger_entries`。

每个 internal input schema 仅暴露已验证的参数，`skip >= 0`、`1 <= limit <= 100`，并为 AI 工具设置更低的实现级最大结果量。输出由新的 AI projection schema 包装，包含 tool 名、筛选摘要、数据摘要及稳定 source reference；不得把 SQLModel entity、删除态明细或无限分页结果交给 sidecar。`include_deleted` 仅在父任务明确允许后可成为工具输入；第一版默认 false。

## 网络与部署边界

现有 `compose.yml` 的 backend 通过 Traefik host router 暴露，未按 path 隔离。实施中：

- sidecar 使用 Docker 服务名访问 FastAPI internal URL；
- sidecar 不配置 Traefik labels 或 host port；
- FastAPI internal endpoint 始终要求 service token + actor grant；
- 与 sidecar 子任务共同在 Traefik 增加 `/internal/ai` 拒绝规则，或采用独立 internal listener；在该部署加固完成前，不得把路径可达性当作安全保证。

## 错误、日志与关联

已有 `RequestIdMiddleware` 将 request ID 写入 state/response。BFF 使用该值创建 `ai_run.request_id`，internal calls 带同一关联 ID。预期错误包括超级管理员拒绝、input validation、AI disabled、grant 拒绝、tool limit、sidecar timeout/health failure；它们均通过全局 AppError handler 返回统一 shape。

结构化日志只包含 run ID、request ID、tool 名、状态、时延和错误类别；不得记录 question 全文、JWT、grant、service token、OpenAI key 或完整库存 payload。

## 兼容、迁移和回滚

- 新 SQLModel models、`models/__init__.py` 导出和 Alembic revision 是同一逻辑变更；migration 在隔离 `_test`/`_pytest` 数据库验证。
- public response schema 会改变 OpenAPI，后续必须生成 frontend client，但前端 task 负责页面消费。
- feature flag 关闭时 public BFF fail closed；停用 router/feature、撤销 internal service token 和 grant key 即可回滚，不触及 inventory 表或既有 inventory endpoints。
- 因此不需要对现有库存服务或写入流程做迁移式重构。

## 设计完成条件

实现前需复核 sidecar 提供的实际 internal tool schemas 与部署方式；若协议字段变化，须同步更新本设计、parent design 和 sidecar 子任务 PRD。稳定的授权/审计模式在实现与检查通过后再沉淀到 `.trellis/spec/` 和 `docs/llm-wiki/`。
