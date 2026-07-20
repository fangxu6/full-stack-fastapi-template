# Requirement Spec - PostgreSQL 数据库规则升级

## Background

- 当前仓库已经有 `docs/rules/数据库规则.md`，但内容更偏“仓库适配说明”，缺少 PostgreSQL 专项设计约束。
- 用户提供了一套更完整的 PostgreSQL 表设计规则，覆盖数据类型、约束、索引、JSONB、分区、RLS 和安全演进等关键点。
- 当前仓库真实模型仍存在 `UUID` 主键基线，直接照搬 PostgreSQL 默认推荐会与现状冲突，需要在规范中明确兼容边界。

## Goals

- 将 `docs/rules/数据库规则.md` 升级为 PostgreSQL 专项数据库规范。
- 明确“PostgreSQL 默认推荐”与“当前仓库 UUID 现状兼容说明”的边界。
- 让数据库规则同时覆盖建模、约束、索引、迁移、OpenAPI client 联动和文档更新流程。

## Scope

- In scope:
  - 重写 `docs/rules/数据库规则.md`
  - 新增本 feature 的最小 spec 文档
  - 更新 `docs/decisions/AI_CHANGELOG.md`
- Out of scope:
  - 修改运行时代码或现有数据库模型
  - 把现有 `UUID` 主键表整体迁移为 `BIGINT`
  - 新增 migration、索引或数据库扩展

## Acceptance Criteria

- AC1: 规范明确 PostgreSQL 的默认类型和禁用类型，包括 `TIMESTAMPTZ`、`NUMERIC`、`TEXT`、identity、JSONB 等。
- AC2: 规范明确 PostgreSQL 侧的关键 gotchas，包括外键列手动建索引、`UNIQUE` 与 `NULL`、snake_case 标识符等。
- AC3: 规范明确新表默认优先 `BIGINT GENERATED ALWAYS AS IDENTITY`，同时写清当前仓库既有 `UUID` 模型的兼容例外。
- AC4: 规范覆盖约束、索引、关系、软删除、分区、RLS、JSONB 和 Schema 演进流程。
- AC5: 文档与当前仓库 `SQLModel + Alembic + FastAPI + OpenAPI client` 工作流保持一致。
- AC6: 文档明确新表自身 `BIGINT` 主键可与既有 UUID 外键共存，并规定业务编号、
  UUID 例外、请求中技术 ID、403/404 与 JavaScript 精度告警边界。

## Constraints

- 不能让规则与当前仓库现有 `user` / `item` 的 `UUID` 主键现实冲突。
- 不能引入 MySQL、旧企业项目模板或本仓库不存在的数据字典流程。
- 规范必须偏执行性，不能只停留在概念摘要。
