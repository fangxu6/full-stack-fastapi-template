# Interface Spec - PostgreSQL 数据库规则升级

## Document Boundary

本次变更不引入新的运行时 API，核心是升级数据库规则文档的职责边界和表达精度。

## Affected Documents

- `docs/rules/数据库规则.md`
- `docs/specs/postgresql-database-rules/01_requirement.md`
- `docs/specs/postgresql-database-rules/02_interface.md`
- `docs/specs/postgresql-database-rules/03_implementation.md`
- `docs/specs/postgresql-database-rules/04_test_spec.md`
- `docs/decisions/AI_CHANGELOG.md`

## Target Contract Assumptions

- 后端数据库事实来源仍以 `SQLModel model -> Alembic migration` 为准。
- 接口契约仍以 `FastAPI request/response model -> OpenAPI schema -> frontend generated client` 为准。
- 文档必须明确：
  - PostgreSQL 默认推荐主键策略
  - 当前仓库既有 `UUID` 模型兼容规则
  - 何时需要同步前端 client

## Compatibility Notes

- 现有 `backend/app/models/user.py` 与 `backend/app/models/item.py` 使用 `UUID` 主键。
- 新规范不能要求在无迁移方案的前提下修改这些既有表。
- 新表若关联既有 `UUID` 表，则沿用 `UUID` 键类型；若是全新业务域且无兼容依赖，可优先评估 `BIGINT IDENTITY`。
