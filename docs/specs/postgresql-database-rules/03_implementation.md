# Implementation Spec - PostgreSQL 数据库规则升级

## Goal Summary

- 把现有数据库规则文档升级为一份更完整的 PostgreSQL 专项规范，同时保留当前仓库的必要兼容说明。

## Planned Changes

- 重写 `docs/rules/数据库规则.md` 的结构与内容。
- 新增对以下主题的明确规则：
  - PostgreSQL 设计原则
  - 命名规范
  - 数据类型选择与禁用类型
  - 主键策略与 UUID 兼容边界
  - 约束、外键、索引与删除策略
  - JSONB、范围类型、分区、RLS
  - Schema 演进流程与安全演进要求
- 新增 `docs/specs/postgresql-database-rules/` 作为本次规则升级的最小规格记录。
- 更新 `docs/decisions/AI_CHANGELOG.md` 记录本次规则升级原因与风险。

## Implementation Notes

- 文档将优先描述 PostgreSQL 默认推荐，而不是简单复述当前模板实现。
- 文档会显式写出当前仓库 `UUID` 主键现状，避免规范与现实冲突。
- 本次不改运行时代码，因此不生成 migration、不调整模型字段类型。

## Non-Goals

- 不把当前仓库强行迁移为 `BIGINT` 主键体系。
- 不引入新的数据库扩展或复杂表结构。
- 不新增单独数据字典系统。
