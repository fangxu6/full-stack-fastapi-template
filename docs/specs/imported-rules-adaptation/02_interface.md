# Interface Spec - 外来规则文档适配

## Document Boundary

本次改造不引入新的运行时接口，核心是重定义 5 份规则文档在当前仓库中的职责边界。

## Target Document Roles

### `docs/rules/项目宪章.md`
- 角色：仓库级工程原则与开发执行阶段约束。
- 关注点：
  - 当前技术栈基线
  - 非平凡变更的 spec-first 流程
  - 分层架构、生成代码边界、验证要求、决策记录方式

### `docs/rules/需求宪章.md`
- 角色：需求确认阶段的高层原则。
- 关注点：
  - 需求如何拆成 `docs/specs/<feature>/01~04`
  - 需求、接口、实现、测试文档之间的责任分工
  - 何时需要更新 spec、何时只需轻量记录

### `docs/rules/需求规则.md`
- 角色：需求文档的实操细则。
- 关注点：
  - `01_requirement.md`、`02_interface.md`、`03_implementation.md`、`04_test_spec.md` 的写法
  - 当前仓库的接口、数据模型、前端集成和变更同步要求

### `docs/rules/需求文档编号规范示例.md`
- 角色：当前 `docs/specs/` 结构的完整示例。
- 关注点：
  - 目录结构
  - 每份 spec 的样例内容
  - 与 OpenAPI client、Alembic、前端页面的联动方式

### `docs/rules/数据库规则.md`
- 角色：当前仓库数据库建模与 schema 变更规则。
- 关注点：
  - `SQLModel + PostgreSQL + Alembic`
  - 命名、关系、UUID、时间、约束、迁移、客户端同步

## Current Repo Contract Assumptions

- 后端接口契约以 FastAPI 的 path/method/request model/response model 为准。
- 前端调用默认通过 OpenAPI 生成 client 与 TanStack Query 组合完成。
- 数据模型变化通过 `SQLModel model -> Alembic migration -> OpenAPI schema -> frontend client regeneration` 串联。
- 重大规则调整记录到 `AI_CHANGELOG.md`；架构级决策可额外使用 ADR。

## Non-Goals

- 不恢复 `/Doc/requirement`、`/Doc/dataDict` 或 `00/101/201/301` 编号体系。
- 不创建新的配置驱动权限系统、统一数据字典中心或企业工作流引擎。
