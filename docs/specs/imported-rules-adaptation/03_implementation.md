# Implementation Spec - 外来规则文档适配

## Goal Summary
- 把 5 份来自其他项目的规则文档转写为当前仓库可执行的版本，消除与真实代码和流程的冲突。

## Planned Changes
- 新增规格目录 `docs/specs/imported-rules-adaptation/`，记录本次文档治理目标与验收标准。
- 重写 `docs/rules/数据库规则.md`，切换到 `SQLModel + PostgreSQL + Alembic` 语境。
- 重写 `docs/rules/需求宪章.md` 与 `docs/rules/需求规则.md`，切换到 `docs/specs/<feature>/01~04` 流程。
- 重写 `docs/rules/需求文档编号规范示例.md`，用当前仓库的 spec 目录示例替换旧的 `/Doc/requirement` 示例。
- 重写 `docs/rules/项目宪章.md`，保留可迁移工程原则，移除 `/speckit`、`featureKey`、Ant Design、MySQL 等另一项目硬编码规则。
- 更新 `docs/decisions/AI_CHANGELOG.md`，记录本次规则体系适配。

## Adaptation Strategy

### 保留并转译
- 需求先澄清目标和边界
- 文档与实现保持同步
- 非平凡改动先有 spec
- 分层架构与关键路径验证
- 重大决策保留审计记录

### 删除或替换
- `/Doc/requirement`、`/Doc/dataDict`、`/temp`
- `00_目录 / 101 / 201 / 301` 体系
- `SQLAlchemy + MySQL + Ant Design + React Router + featureKey + usePermission + speckit`
- 固定的 `code/message/data` 响应包装
- 单据主从表、`Master/Detail`、`Common_Enum` 等企业项目特有约束

### 当前仓库锚点
- 需求流程：`AGENTS.md` 与 `docs/specs/feature-template/`
- 后端技术基线：`backend/README.md`、`backend/pyproject.toml`
- 前端技术基线：`frontend/README.md`、`frontend/package.json`
- 前端主规范：`docs/rules/前端开发规范.md`
- 决策记录：`docs/decisions/AI_CHANGELOG.md`、`docs/decisions/ADR-xxxx.md`

## Non-Goals
- 不把当前仓库改造成外来项目的企业规范结构。
- 不新增数据字典目录或权限配置文件体系。
- 不修改代码以适配旧文档，而是反过来让文档适配当前仓库。
