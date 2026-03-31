# Test Spec - 外来规则文档适配

## Validation Scope
- 验证 5 份重写后的规则文档是否与当前仓库真实技术栈和流程一致。
- 验证文档之间职责边界是否清晰，不再互相冲突。

## Review Checklist
- TC1: 文档中不再把 MySQL、SQLAlchemy、Ant Design、React Router、`featureKey`、`usePermission`、`/speckit`、`/Doc/dataDict` 当作当前仓库默认前提。
- TC2: `需求宪章.md` 与 `需求规则.md` 明确以 `docs/specs/<feature>/01_requirement.md` 到 `04_test_spec.md` 为主结构。
- TC3: `需求文档编号规范示例.md` 的示例目录与当前 `docs/specs/` 结构一致。
- TC4: `数据库规则.md` 明确使用 `SQLModel + PostgreSQL + Alembic`，并允许符合业务语义的外键、UUID 和迁移流程。
- TC5: `项目宪章.md` 中的工程原则能与 `AGENTS.md`、`前端开发规范.md`、后端 README 对齐。
- TC6: 文档中的 API 契约说明与当前 FastAPI + OpenAPI client 现实相容，而不是强制 `code/message/data` 包装。
- TC7: 本次改造在 `AI_CHANGELOG.md` 中留下清晰决策记录。

## Manual Verification
- 逐份检查是否仍残留明显的外来项目路径、命名或角色假设。
- 检查新文档是否可以指导当前仓库新增功能的需求、接口、实现和测试说明。
- 检查是否存在与现有主规范冲突的“二套规则”。
