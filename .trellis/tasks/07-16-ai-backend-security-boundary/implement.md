# AI 后端安全边界实施计划

## 前置与启动门槛

- 本子任务的 PRD/design 已完成；在用户批准前不运行 `task.py start`。
- 执行前加载 `trellis-before-dev`，复查 backend specs、父级 contract、sidecar 的最终 internal tool schema 和 OpenAI data-control 状态。
- 仅在 `POSTGRES_DB` 为隔离 `_test` 或 `_pytest` 数据库时运行 pytest；当前测试 fixture 会清理数据库。

## 实施步骤

1. **冻结契约和配置**
   - 与 sidecar child 确认 tool names、input/output schemas、最大工具调用数、HTTP headers、expiry、issuer/audience 和 structured result/error shape。
   - 在 `core/config.py` 增加 fail-closed AI settings（enabled、sidecar URL、internal service token、grant signing key、TTL、max calls）；为 production 默认/缺失配置写验证与测试。
   - 增加语义服务不可用/AI disabled error，保持全局 error shape。

2. **新增模型、schemas 与 migration**
   - 在 `models/ai.py` 添加 `ai_run`、`ai_tool_call` 及 audit fields，更新 `models/__init__.py`；所有新增 table/index/constraint/sequence 名称以 `ai_` 开头。
   - 在 `schemas/ai.py` 分别定义 public query/response、internal grant/tool input、tool output/source summary 和 audit DTO；禁止 route-local `dict[str, Any]` 合同。
   - 生成以 AI 前缀对象为主题的 Alembic revision；验证 upgrade/downgrade 与用户 foreign keys、`ai_` 索引/约束、UTC timestamps、counter constraints 和 soft-delete/audit rules。

3. **实现 AI application service**
   - 创建/结束 run、记录 tool call、生成并验证 actor grant、原子消费 tool slot。
   - 添加 sidecar client abstraction，带 request ID、超时、有限重试和无敏感信息日志；不在 route 内执行 HTTP 或业务编排。
   - 将 service token 使用常量时间比较；grant 验证 signer、expiry、issuer/audience、scope、run/user 绑定与 call limit。

4. **实现 routers 与 inventory projections**
   - 添加 public `/api/v1/ai/inventory/query` router，以 `get_current_active_superuser`、typed request/response 与 service delegation 实现。
   - 添加 internal read router，仅接收 service-authenticated request；逐工具调用 existing inventory service，不引入 SQL/ORM 直查。
   - 统一 enforce AI 结果上限、`include_deleted=False`、输入 pagination/filter validation 和 stable source summaries。
   - 在 `api/main.py` 注册 public router；internal path 的 registration 与 proxy-deny/network strategy 和 sidecar task 一并落地。

5. **测试与 client contract**
   - 添加 API/service tests：anonymous/normal/inactive/superadmin、422、403、feature disabled、sidecar failure、grant expired/forged/replayed/out-of-scope、call-limit、所有五个 read tools。
   - 添加 migration/audit tests：actor fields、request ID correlation、atomic limit、无 secret/raw payload persistence。
   - 验证 inventory write endpoints 没有在 AI registry/route 中被引用。
   - 运行 client generation；将生成的 consumer changes 交给 frontend child，不手改 `frontend/src/client/**`。

6. **部署联调与回滚验证**
   - 使用测试 sidecar/mock 验证 BFF→internal tools 链路、request ID 关联和 fail-closed 行为。
   - 与 sidecar task 验证 service token/grant、Docker service DNS、Traefik deny/internal listener 和无 direct database access。
   - 验证关闭 feature、撤销 token/key 后现有 inventory API 与数据不变。

## 验证命令与门槛

- 后端静态门：在 `backend/` 目录运行 `bash scripts/lint.sh`。
- 测试前显式设置安全 `POSTGRES_DB`，运行 focused AI tests，再运行 `bash scripts/test.sh` 或解释跳过的原因。
- public schema/OpenAPI 变化后，从仓库根运行 `bash ./scripts/generate-client.sh`，并确认不会手改 generated client。
- 检查 `detail + request_id`、`X-Request-ID`、403/422/503 路径和日志无 secret。
- 将 sidecar integration 和 Docker/Traefik 验证留给相关子任务的 cross-task review；本 task 不负责安装 Mastra 或配置 OpenAI key。

## 风险与停止条件

- service token 或 grant 不能可靠验证、call slot 不能原子消费、或 internal path 仅依赖网络隐藏：停止实施并回到设计。
- migration 不能在隔离库安全通过、审计会保存完整库存数据/secret、或 public error contract 漂移：停止并回滚该子任务变更。
- 若 sidecar contract 需要可变工具、无限调用、普通用户或直接 DB access，属于父级范围变更，不能在本子任务中放宽。

## 当前执行进度（2026-07-17）

已完成的最小安全切片：

- `AI_ENABLED` 的 fail-closed 配置校验、503 错误契约与超级管理员 public BFF 入口；
- `ai_run` / `ai_tool_call` 模型、显式 `ai_` 数据库对象命名和
  `create_ai_audit_tables` migration；已在隔离 `aiadmin_test` 完成
  downgrade/upgrade 验证；
- 审计 run 创建、问题 SHA-256 摘要、原子 tool-slot 预留、短时签名 actor
  grant（run/user/scope/issuer/audience 绑定）和常量时间 service-token 比较；
- internal tool 的服务层授权入口：必须先完成 service-token 与 grant 验证，
  才能原子预留对应 run 的调用额度；
- 首个真实 internal read endpoint：`POST /api/v1/internal/ai/inventory/balances`
  使用受限 DTO（最多 20 条）、不进入 public OpenAPI schema，并只委托既有
  `inventory_service.list_balances`；
- 单位 projection：`processing-units` 与 `receiving-units` 各自绑定独立 scope，
  复用同一受限单位 DTO，并仅委托现有 inventory unit service；
- 模型/服务/API focused tests、完整后端 pytest（144 passed）及 mypy、ty、Ruff
  静态门。

下一步从 internal read router 开始：先为 service-token + grant 依赖与五个
白名单 projection schema 编写 red tests，再复用现有 inventory service；随后实现
sidecar client、BFF 编排与失败状态收尾。Docker 级测试仍待具备 Docker CLI 的环境执行。
