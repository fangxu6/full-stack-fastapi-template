# e2e-api-tests.md — 跨端集成 API E2E 计划

本任务**不新增或修改任何后端接口**（Out of Scope）。但它是跨层复杂任务：契约从 `frontend/src/client` 迁到 `packages/contract`，并由 Web 与 App 两端共同消费。因此仍需跨层 E2E 验证——用**既有**接口证明契约迁移后两端行为正确。

来源：`.trellis/spec/templates/e2e-api-tests-template.md`。

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Web target: `http://localhost:5173`
- App target: Android 真机 + Expo Go（扫码验证需真机，模拟器不支持 `expo-camera`）
- Isolation: 使用任务独立的隔离环境——独立数据库（**不得写入开发库**）与独立的 Redis 库索引；后端进程独立于任何部署运行时。若本机无可用隔离环境，**只有在实际尝试之后**才可记录具体阻塞项。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `GET /api/v1/utils/health-check/` | 无 | 无 | `200` | 无 | 非 200 即环境未就绪，停止后续用例 |
| E2E-002 | `POST /api/v1/login/access-token` | 隔离库中一个具备 `inventory.documents.read` + `inventory.balances.read` 的用户 | `username` + `password`（form-encoded，OAuth2 password flow） | `200`，body 含 `access_token`、`token_type: "bearer"` | 无写入 | 错误口令返回 `400`/`401`；响应体不得泄露密码或哈希 |
| E2E-003 | `GET /api/v1/iam/permissions`（经 `myPermissionsQueryOptions`） | 同 E2E-002 | `Authorization: Bearer <token>` | `200`，权限码集合包含 `inventory.documents.read` | 无 | 无 token → `401`；这是 App 与 Web 共用同一 query options 的验证点 |
| E2E-004 | `GET /api/v1/inventory/documents?document_number=<X>` | 隔离库中一条 `document_number = X` 的单据 | `Authorization: Bearer <token>` | `200`，返回列表且包含该单据 | 无 | **扫不到的单据号**（如 `ZZZ-NOT-EXIST`）→ `200` + 空列表（不是 `500`）；App 必须据此给出"未命中"提示（AC9） |
| E2E-005 | `GET /api/v1/inventory/documents/{document_id}` | 取 E2E-004 返回的单据 id | `Authorization: Bearer <token>` | `200`，明细字段与列表项一致 | 无 | 不存在的 id → `404`，不得 `500` |
| E2E-006 | `GET /api/v1/inventory/balances/raw` | 隔离库中有余额数据 | `Authorization: Bearer <token>` | `200` | 无 | — |
| E2E-007 | RBAC 拒绝：`GET /api/v1/inventory/balances/raw` | 一个**只有** `inventory.documents.read` 的用户（无 `inventory.balances.read`） | `Authorization: Bearer <token>` | `403` | 无写入；数据不得部分返回 | 服务端拒绝必须真实生效——App 隐藏入口**不能**替代服务端校验（AC4） |
| E2E-008 | RBAC 拒绝：`GET /api/v1/inventory/documents` | 一个无 `inventory.documents.read` 的用户 | `Authorization: Bearer <token>` | `403` | 无 | 同上 |
| E2E-009 | 契约生成一致性（跨层） | 子任务 1 完成后的工作区 | `bash ./scripts/generate-client.sh` | 命令成功 | `git diff --exit-code` 为空 | 有 diff 即生成链路未完整迁移（旧路径残留），必须修复 |
| E2E-010 | Web 侧回归（跨层） | 同上 | `bun run build`、`bun run lint`、`bun test scripts/check-thin-routes.test.ts`、`python hooks/run_quality_hooks.py --json` | 全部通过 | 无 | 任一失败即 AC6 不满足 |

## 与验收标准的映射

| AC | 由哪些用例覆盖 |
|---|---|
| AC2 | E2E-002（真实 JWT）+ App 侧断言 token 落 `expo-secure-store` |
| AC3 | E2E-004、E2E-005、E2E-006（真实业务数据经同源契约渲染） |
| AC4 | E2E-003（入口可见性依据）+ E2E-007、E2E-008（服务端拒绝仍生效） |
| AC5 | E2E-009、E2E-010（Web 侧行为不变） |
| AC6 | E2E-010 |
| AC9 | E2E-004 的空列表分支（未命中提示）+ 真机扫码 |

## Execution

- 先起隔离环境，跑 E2E-001 确认就绪；未就绪则记录阻塞项，不得把环境失败记为通过。
- 按 ID 顺序执行；E2E-002 的 token 供 E2E-003 至 E2E-008 复用。
- E2E-004 与 E2E-007 需要**两个不同权限组合的用户**，必须在隔离库中分别准备（这是 AC4 的核心验证手段）。
- E2E-009、E2E-010 是跨层一致性用例，不需要后端运行。
- 把命令输出与结论记入本任务的验证笔记或子任务的 `implement.md`。

## 执行归属

| 用例 | 在哪个任务执行 |
|---|---|
| E2E-001 ~ E2E-008 | 子任务 `10-10-mobile-app-slice`（App 消费端落地时） |
| E2E-009、E2E-010 | 子任务 `10-10-cross-platform-kernel`（契约迁移后立即） |
| 全量复跑 | 父任务 `10-10-react-native-app` 集成复核 |

子任务 `10-10-mobile-app-slice` 的 `e2e-api-tests.md` 引用本文件，不重复定义用例。
