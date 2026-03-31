# Requirement Spec - 外来规则文档适配

## Background
- `docs/rules/` 中有 5 份从其他项目拷贝过来的规则文档，包含大量与当前仓库不一致的技术栈、目录结构和流程假设。
- 这些文档继续保留在规则目录下但不做适配，会对后续实现、评审和 AI 协作产生持续误导。

## Goals
- 将 5 份外来规则文档改造成当前仓库可直接使用的版本。
- 仅保留可迁移的高层原则，删除或重写与当前仓库冲突的栈、接口、数据库和流程假设。
- 让这些文档与 `AGENTS.md`、`docs/specs/` 流程、`docs/rules/前端开发规范.md`、`AI_CHANGELOG.md` 保持一致。

## Scope
- In scope:
  - 重写 `docs/rules/数据库规则.md`
  - 重写 `docs/rules/需求宪章.md`
  - 重写 `docs/rules/需求文档编号规范示例.md`
  - 重写 `docs/rules/需求规则.md`
  - 重写 `docs/rules/项目宪章.md`
  - 记录本次文档治理决策到 `docs/decisions/AI_CHANGELOG.md`
- Out of scope:
  - 修改后端或前端运行时代码
  - 新增数据库迁移、权限系统或新框架
  - 恢复外来项目的 `/Doc`、`dataDict`、`/speckit` 等工作流

## Acceptance Criteria
- AC1: 5 份文档不再包含与当前仓库冲突的核心技术栈假设，例如 MySQL、SQLAlchemy、Ant Design、React Router、`featureKey`、`usePermission`、`/Doc/dataDict`、`/speckit`。
- AC2: 文档中的规则能映射到当前仓库的真实基线：`SQLModel + PostgreSQL + Alembic + FastAPI + Vite + React 19 + TanStack Router/Query + Tailwind/shadcn + OpenAPI 生成 client`。
- AC3: 需求相关文档统一以 `docs/specs/<feature>/01_requirement.md` 到 `04_test_spec.md` 为主流程，不再与 `00/101/201/301` 体系混用。
- AC4: 数据库与接口规则明确体现当前仓库的模型、迁移、OpenAPI 和前端生成 client 联动方式。
- AC5: `项目宪章.md`、`需求宪章.md`、`需求规则.md` 和示例文档之间的职责边界清晰，读者可以据此开展当前仓库的文档驱动开发。

## Constraints
- 以当前仓库已有文档和代码为准，不为了迁就外来规则保留错误假设。
- 文档改造应尽量复用仓库已有术语和流程。
- 变更聚焦在文档和决策记录，不扩大为新的治理体系重构。

## Risks & Rollout
- 风险：旧文档中少量有价值的抽象原则可能在重写时被弱化。
- 缓解：保留可迁移原则，但必须通过当前仓库语境重写，而不是机械移植。
- 风险：后续如果代码栈继续演进，这些新文档仍可能再度过时。
- 缓解：将本文档与 `AI_CHANGELOG.md`、`AGENTS.md` 的主流程对齐，方便增量维护。
