# Test Spec - PostgreSQL 数据库规则升级

## Validation Scope

- 验证新的数据库规则文档是否同时满足 PostgreSQL 专项设计要求和当前仓库现实约束。

## Review Checklist

- TC1: 文档是否明确 PostgreSQL 默认推荐类型，并列出禁用类型。
- TC2: 文档是否明确写出外键列必须手动建索引。
- TC3: 文档是否覆盖 `UNIQUE` 与 `NULL`、JSONB、部分索引、表达式索引、范围类型等 PostgreSQL 特性。
- TC4: 文档是否明确“新表默认优先 `BIGINT IDENTITY`，现有 `UUID` 表保持兼容”的边界。
- TC5: 文档是否把 Schema 变更流程与 `docs/specs/`、Alembic、OpenAPI client 联动写清楚。
- TC6: 文档是否避免与当前仓库真实模型、README 和 AGENTS.md 冲突。
- TC7: `AI_CHANGELOG.md` 是否记录了本次规则升级。
- TC8: 文档是否区分新表自身主键和外键目标类型，并定义实体、明细行、纯关联表的
  主键边界。
- TC9: 文档是否定义未来模块的 identity、DTO 422、授权 403/404、生成客户端和
  `MAX(id)` 告警测试点。

## Manual Verification

- 检查文档中是否仍残留 MySQL 或旧项目特定假设。
- 检查兼容说明是否足够具体，避免读者误以为必须立刻改造现有 UUID 表。
- 检查内容是否可直接指导后续新增表、改表和 migration 设计。
