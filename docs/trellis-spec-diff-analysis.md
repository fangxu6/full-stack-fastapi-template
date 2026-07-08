# Trellis Spec 差异分析：`.trellis-other/spec` vs `.trellis/spec`

> 目的：比较 `D:\Workspace\JSE_AI_Speckit` 的 `.trellis-other/spec` 与当前项目 `.trellis/spec` 的差异，筛出与技术栈无关、值得迁移到当前 FastAPI/React 项目的规范模式。

## 结论摘要

`.trellis-other/spec` 的优势不只是“文件更多”，而是规范组织方式更接近可执行知识库：

- 它有全局目录和维护日志：`index.md`、`log.md`。
- 它把大量经验沉淀成“场景契约”：`Scope / Trigger`、`Signatures`、`Contracts`、`Validation & Error Matrix`、`Good/Base/Bad Cases`、`Tests Required`、`Wrong vs Correct`。
- 它在质量规范里覆盖了文件大小、注释标准、批处理性能、配置一致性、文档同步、归档复盘等技术栈无关的交付门禁。
- 它的索引不是只列通用层，而是把“触发条件 -> 应读规范”写进 Read Order，能指导 AI 在任务前加载更精确的上下文。

当前 `.trellis/spec` 的优势是已经贴合本项目 FastAPI/React 技术栈，并且有更准确的本地代码锚点。后续改造不应复制 JSE/PMS/Tooling 业务文本，而应迁移其“规范形态”和“交付门禁”。

## 规模差异

| 目录 | Markdown 文件数 | 总行数 | 形态 |
| --- | ---: | ---: | --- |
| `.trellis/spec` | 17 | 1634 | backend/frontend/guides 三层，偏架构方向和通用检查 |
| `.trellis-other/spec` | 60 | 9036 | 全局 catalog/log + 通用层 + 包级层 + 大量场景契约 |

当前项目只有一个场景契约风格文件：

- `.trellis/spec/frontend/route-permission-navigation-contract.md`

`.trellis-other/spec` 则大量采用该形态，覆盖后端、前端、跨层、业务流程、OpenAPI、类型安全、事件门禁、导入导出、状态流转等主题。

## 文件结构差异

### 当前项目

当前 `.trellis/spec` 主要文件：

- `backend/*.md`：目录、数据库、错误、日志、质量。
- `frontend/*.md`：目录、组件、hook、状态、类型、质量、路由权限导航契约。
- `guides/*.md`：代码复用、跨层思考。

特点：

- 每个文件较短，便于快速读完。
- 很多规则已经绑定本项目真实代码路径，例如 `backend/app/**`、`frontend/src/**`、`scripts/generate-client.sh`。
- 规范仍偏“层级指南”，缺少足够多的“具体场景契约”。

### `.trellis-other/spec`

`.trellis-other/spec` 多出的关键类别：

- 全局维护：
  - `index.md`
  - `log.md`
- 包级规范：
  - `backend/JSECommon/backend/**`
  - `frontend/JSE_UI_AI/frontend/**`
- 后端场景契约：
  - `backend/generic-http-event-callback-gate.md`
  - `backend/event-log-trace-filter.md`
  - `backend/openapi-cn-docs.md`
  - `backend/type-safety.md`
  - `backend/datafile-ft-json-parser.md`
  - 多个 PMS/Tooling/Training 场景契约
- 前端场景契约：
  - `frontend/generic-http-event-callback-gate.md`
  - `frontend/pms-checklist-option-visibility.md`
  - `frontend/pms-work-order-claim-domain.md`
  - `frontend/training-statistics-display-config.md`
- 指南扩展：
  - `guides/codex-session-subagent-guide.md`

其中 PMS、Tooling、JSE、Vue、Element Plus、MySQL、Celery、Redis 等内容是项目特定内容，不应直接迁移；但文档结构和若干交付门禁可以迁移。

## 关键差异

### 1. 全局 catalog 和维护日志

`.trellis-other/spec/index.md` 是全局 spec catalog，按 Layer Indexes、Backend Specs、Frontend Specs、Guides Specs 汇总所有规范，并说明使用顺序。

`.trellis-other/spec/log.md` 是 append-only 维护日志，记录每次规范 ingest、lint、update 的时间和原因。

当前项目缺失这层机制。影响是：

- AI 需要从目录树猜测该读哪些 spec。
- 规范更新没有集中记录，难以判断某条规则从哪个任务沉淀而来。
- 后续如果引入 `spec_wiki.py`，当前项目还没有配套的 `index.md` / `log.md`。

可迁移做法：

- 为当前项目生成 `.trellis/spec/index.md`，用当前 FastAPI/React 规范重建 catalog。
- 添加 `.trellis/spec/log.md`，记录规范更新、lint、任务复盘沉淀。
- 在 workflow 里要求 spec 更新后运行 catalog/lint/log 维护命令。

### 2. 场景契约粒度

`.trellis-other/spec` 的许多文件都采用同一套“可执行契约”模板：

1. `Scope / Trigger`
2. `Signatures`
3. `Contracts`
4. `Validation & Error Matrix`
5. `Good / Base / Bad Cases`
6. `Tests Required`
7. `Wrong vs Correct`

当前项目只有 `frontend/route-permission-navigation-contract.md` 基本具备这种结构。其他 backend/frontend 指南更多是 Required Patterns、Forbidden Patterns、Code Anchors。

可迁移做法：

- 把这个模板作为当前项目新增场景契约的标准。
- 优先用于高风险跨层规则，例如：
  - OpenAPI client regeneration contract
  - request_id error contract
  - route/permission/navigation sync
  - backend schema -> generated client -> React form/table round trip
  - auth/logout/token persistence
  - import/export or bulk operation validation

### 3. Read Order 从“层级顺序”变成“触发条件路由”

当前项目的 `backend/index.md` 和 `frontend/index.md` 主要说明读哪些基础指南。

`.trellis-other/spec/backend/index.md` 和 `frontend/index.md` 不只列文件，还把具体触发条件写进 Read Order，例如：

- 如果触及某类事件回调，读对应契约。
- 如果触及某类状态流转，读对应契约。
- 如果触及 OpenAPI 输出，读对应契约。
- 如果触及某类前端配置、按钮或路由，读对应契约。

可迁移做法：

- 当前项目应把 Read Order 扩展成任务路由表：
  - backend API/schema/error/logging 变化读哪些文档。
  - frontend route/menu/permission 变化读哪些文档。
  - OpenAPI/client 变化读哪些文档。
  - 跨层功能读哪些 guides 和场景契约。

### 4. 质量规范更像交付门禁

当前 `.trellis/spec/backend/quality-guidelines.md` 已有：

- keep routes thin
- preserve unified errors and request correlation
- API contract changes require client generation review
- forbidden patterns
- minimum validation expectations

`.trellis-other/spec/backend/quality-guidelines.md` 进一步增加了技术栈无关的交付门禁：

- 文件大小分级和手写业务代码过大时的拆分要求。
- 注释要求：解释 why、invariants、side effects、rollback、compatibility，而不是复述代码。
- 性能和批处理：优先 set-based SQL / batch query，避免 N+1、避免把完整列表拉到 Python 再过滤分页。
- Polish & Archive Gates：收尾时检查代码一致性、配置一致性、文档同步，并判断是否需要把可复用规则归档。
- Code Review Checklist：把权限、UUID、软删、审计、迁移、响应字段、配置同步、文档同步、归档判断都列成检查项。

可迁移做法：

- 给当前项目 backend/frontend quality guidelines 增加“交付门禁”区块。
- 当前项目不要照搬 `BINARY(16)`、`config_Feature.json`、`speckit.archive` 等 JSE 特定项；应替换成：
  - SQLModel/Alembic migration review
  - generated OpenAPI client regeneration
  - route/menu/permission alignment
  - docs/llm-wiki 或 `.trellis/spec` 更新判断
  - Docker Compose / backend / frontend validation commands

### 5. 技术栈无关的“配置一致性”意识更强

`.trellis-other/spec` 多处要求：

- 路由、按钮、菜单、表头、权限 key、后端配置文件保持一致。
- 修改配置型元数据后要运行生成/检查命令。
- Polish 阶段必须显式说明文档同步是否适用。

当前项目也有类似风险：

- React route、router guard、menu config、permission helper 可能漂移。
- Backend schema 和 generated client 可能漂移。
- OpenAPI JSON 和 frontend client 可能漂移。

可迁移做法：

- 把“配置一致性”写成当前项目自己的检查项：
  - route guard、menu config、permission helper 同步。
  - OpenAPI schema、generated client、frontend usage 同步。
  - docs 或 Trellis spec 是否需要更新。

### 6. 跨层思考指南：`.trellis-other` 更抽象，当前项目更具体

当前 `guides/cross-layer-thinking-guide.md` 已经贴合本项目：

- FastAPI route -> service -> CRUD/model -> schema -> OpenAPI client -> React query/page
- `detail + request_id`
- generated client regeneration
- route/menu/permission 同步

`.trellis-other` 的跨层指南更抽象，强调：

- Source -> Transform -> Store -> Retrieve -> Transform -> Display
- 每个边界的格式、风险、验证责任。
- list/tree/option 读取接口不能被源管理页面的 read 权限误伤跨页面消费者。

可迁移做法：

- 保留当前项目具体链路。
- 补充更通用的数据流模板，适用于不一定走 OpenAPI client 的任务。
- 谨慎评估 list/option 权限规则是否适合当前项目；原则可迁移，但权限模型不能直接照搬。

### 7. 代码复用指南：`.trellis-other` 多了“批量修改后回查”和“非对称机制漂移”

当前 `guides/code-reuse-thinking-guide.md` 已经很好：

- 要先用 CodeGraph / `rg` 搜索。
- 抽象条件和 false sharing 风险更贴合当前项目。
- 后端 services/crud、前端 shared/features/platform 的边界清楚。

`.trellis-other` 多了两个通用提醒：

- 批量改多个文件后，要回查是否漏掉相同模式。
- 两套机制产出同一文件集合时，一套自动、一套手工，目录结构变化容易只更新一边。

可迁移做法：

- 将“批量修改后回查”加入当前 code reuse guide。
- 将“非对称机制漂移”加入当前 guide，尤其适用于：
  - generated client / OpenAPI
  - route tree generation
  - task/template files
  - docs index 和 spec catalog

### 8. 类型安全：`.trellis-other` 有后端 type-safety 专篇

当前项目有 `frontend/type-safety.md`，但 backend 没有独立 `type-safety.md`，相关内容分散在 database/quality/error 指南里。

`.trellis-other/spec/backend/type-safety.md` 的可迁移结构包括：

- Source of Truth
- Required Patterns
- Common Patterns
- Forbidden Patterns
- Review Checklist
- 高风险场景契约

不可直接迁移的内容：

- `BINARY(16)` UUID bytes 规则。
- PascalCase legacy contract。
- JSE/PMS 具体 schema 和 service。

可迁移做法：

- 新增当前项目 backend type-safety 规范，围绕：
  - SQLModel/Pydantic schema 是 API IO source of truth。
  - `uuid.UUID`、datetime、Decimal、nullable 字段序列化边界。
  - service/public helper 要有明确类型签名。
  - 不用 `Any` 或 route-local dict 绕过 schema。
  - OpenAPI/client 变更后生成并编译前端。

### 9. 测试要求更可执行

当前项目规范通常写“运行 lint/type-check/tests”或“验证相关路径”。

`.trellis-other/spec` 的场景契约通常直接列：

- Service regression
- Route/API regression
- Frontend component/service tests
- E2E smoke
- Good/Base/Bad cases 对应的测试点

可迁移做法：

- 对每个新增场景契约要求 `Tests Required`。
- 对跨层任务要求至少列出：
  - backend service/API 测试
  - frontend component/page 测试
  - generated client/build 验证
  - E2E 或 smoke 验证条件

### 10. `.trellis-other` 有很多“任务沉淀型规则”

`.trellis-other` 的很多规范明显来自真实 bug 或 review 之后的沉淀，例如：

- OpenAPI 文档后处理必须同时覆盖多个入口。
- 前置门禁必须在不可逆副作用前执行。
- 阻塞成功后要避免同步/异步重复回调。
- 批量导入要把软删除唯一键冲突转成业务错误。

当前项目的规范更多是一次性架构刷新产物，任务沉淀型规则还少。

可迁移做法：

- 每次任务完成后判断是否产生“可复用规则 / gotcha / review lesson”。
- 如果有，优先追加到 `.trellis/spec` 的具体场景契约，而不是只写在聊天记录或任务总结里。

## 与技术栈无关、值得迁移的规范模式

| 模式 | 价值 | 当前项目落点 |
| --- | --- | --- |
| 全局 spec catalog | 降低 AI 找规范成本 | `.trellis/spec/index.md` |
| spec maintenance log | 追踪规则来源和更新时间 | `.trellis/spec/log.md` |
| 场景契约模板 | 把经验变成可执行检查 | 新增 `*-contract.md` |
| Scope / Trigger | 明确什么时候必须读某规范 | 各 layer index 的 Read Order |
| Validation & Error Matrix | 提前定义边界条件和错误形态 | API/error/import/export/auth 规则 |
| Good/Base/Bad Cases | 防止只覆盖 happy path | 场景契约和测试计划 |
| Tests Required | 把规则绑定到验证命令 | 每个高风险契约 |
| Wrong vs Correct | 让 AI 快速避开常见错法 | 场景契约末尾 |
| 文件大小与拆分门禁 | 防止长期膨胀 | backend/frontend quality guidelines |
| why/invariant 注释标准 | 提升维护性 | backend/frontend quality guidelines |
| 批处理和 N+1 检查 | 防止性能退化 | backend quality guidelines |
| 配置一致性检查 | 防止路由/菜单/权限/API 漂移 | frontend/backend quality guidelines |
| Polish 阶段同步 | 防止代码完成但文档/规范落后 | workflow + quality guidelines |
| 任务后规则归档 | 让 bug fix 变成长期知识 | `.trellis/spec` + docs/llm-wiki |

## 不应直接迁移的内容

以下内容属于 `.trellis-other` 项目的技术栈或业务上下文，不能直接进入当前项目：

- `backend/JSECommon/**`、`frontend/JSE_UI_AI/**` 路径。
- Vue 3、Pinia、Element Plus、JSE compact UI 等前端栈规则。
- MySQL、Celery、Redis、Loguru、`BINARY(16)` UUID bytes 等后端栈规则。
- PMS、Tooling、Training、SQDM、WXWork 等业务域契约。
- `9000` / `5174` / pm2 `fastapi-app` 等运行时假设。
- `speckit.archive`、`.specify/memory/constitution.md`，除非当前项目明确引入同等机制。
- `/home/hq/workspaces/.venv/bin/` 等环境路径。

## 建议的当前项目改造路线

### 第一阶段：引入规范管理骨架

1. 引入或实现 `spec_wiki.py` 后生成 `.trellis/spec/index.md`。
2. 新增 `.trellis/spec/log.md`。
3. 在 workflow 中规定 spec 更新后执行 index/lint/log。

### 第二阶段：统一场景契约模板

1. 把当前 `frontend/route-permission-navigation-contract.md` 作为模板源。
2. 提炼一个通用模板，要求包含：
   - Scope / Trigger
   - Signatures / Interfaces
   - Contracts
   - Validation & Error Matrix
   - Good/Base/Bad Cases
   - Tests Required
   - Wrong vs Correct
3. 在 guides 或 README 中说明新增场景契约何时使用。

### 第三阶段：补齐技术栈无关的质量门禁

优先补充到当前项目：

- `backend/quality-guidelines.md`
  - 文件大小和拆分门禁
  - 注释标准
  - 批处理 / N+1 检查
  - OpenAPI/client/document sync 检查
- `frontend/quality-guidelines.md`
  - route/menu/permission/config 同步检查
  - generated client 使用检查
  - UI 状态和错误路径检查
- `guides/code-reuse-thinking-guide.md`
  - 批量修改后回查
  - 非对称机制漂移 gotcha

### 第四阶段：新增当前项目自己的场景契约

建议优先新增：

1. Backend OpenAPI Client Regeneration Contract
2. Unified Error Request ID Contract
3. Frontend Route Permission Navigation Contract 扩展版
4. Backend Type Safety Contract
5. Import/Export or Bulk Mutation Contract
6. Auth Token / Logout / Current User State Contract

这些契约都要基于当前项目真实代码路径和验证命令写，不从 `.trellis-other` 拷业务文本。

## 最终判断

`.trellis-other/spec` 更成熟的地方，是它把“踩过的坑”写成了可触发、可验证、可回归测试的规则。当前项目不缺基础规范，缺的是：

- spec catalog / log 这类维护机制；
- 更多场景级契约；
- 更强的质量门禁；
- 任务后把经验回写成长期规则的流程。

后续应迁移“规范写法”和“检查机制”，而不是迁移 JSE_AI_Speckit 的业务规范本身。
