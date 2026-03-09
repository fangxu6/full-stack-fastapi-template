# Requirement Spec - Backend 重构补档

## Background
- backend 已完成一次结构化重构，核心目的是将业务逻辑从路由层下沉到服务层，并把依赖注入、数据模型、接口 DTO 解耦。

## Goals
- 明确并落地分层架构：`Route -> Service -> CRUD -> Model`。
- 引入独立 `schemas/` 作为 API 数据契约层，降低数据库模型与接口模型的耦合。
- 将依赖注入拆分到 `api/dependencies/`，提升复用性与可维护性。
- 在不破坏既有 API 行为的前提下完成重构。

## Scope
- In scope:
  - 拆分与规范化 `models/`、`crud/`、`services/`、`api/dependencies/`。
  - 将 users/login/items 路由中的业务编排迁移到 service 层。
  - 新增/完善架构与规范文档（`ARCHITECTURE.md`、`CODING_STANDARDS.md`、`backend/README.md`）。
- Out of scope:
  - 新增业务功能或新增公开 API。
  - 数据库 schema 的业务性变更与迁移。
  - 前端交互和页面改造。

## Acceptance Criteria
- AC1: 主要后端路径遵循 `Route -> Service -> CRUD -> Model`，路由层仅保留输入/输出与状态码编排。
- AC2: 依赖注入模块化完成，`api/dependencies/` 提供可复用依赖，`api/deps.py` 保持兼容入口。
- AC3: API 数据契约由 `schemas/` 显式承载，鉴权、用户、条目 DTO 可独立于 DB 表结构演进。
- AC4: 重构后既有接口行为保持兼容（路径、方法、主要响应语义不变）。

## Constraints
- 不引入破坏性变更；优先保证运行与调用兼容。
- 变更聚焦架构与边界，不做无关批量格式化。
- 遵循项目现有 Python 类型标注与分层规范。

## Risks & Rollout
- 风险：分层迁移过程中可能出现导入路径错误、依赖注入断链、异常映射不一致。
- 缓解：通过分模块提交、文档同步、回归测试（鉴权/用户/items）逐步验证。
- 回滚：可按提交粒度回退（先回退 route/service 迁移，再回退依赖与 schema 拆分）。
