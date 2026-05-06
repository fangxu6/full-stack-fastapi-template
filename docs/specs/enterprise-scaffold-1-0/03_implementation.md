# Implementation Spec

## Goal Summary
- 基于当前仓库现状，分批将模板型项目升级为模块化企业脚手架，而不是直接进入微服务拆分。
- 先建立稳定的平台骨架和治理底盘，再补 IAM / RBAC、系统管理、审计日志、文件中心，并最终把现有 `users/items/docs` 迁成标准样板模块。
- 保持现有 API、前端页面和 generated client 的协作方式，在增量演进中完成结构升级。

## File Changes
- 新增规范文档：
  - `docs/specs/enterprise-scaffold-1-0/01_requirement.md`
  - `docs/specs/enterprise-scaffold-1-0/02_interface.md`
  - `docs/specs/enterprise-scaffold-1-0/03_implementation.md`
  - `docs/specs/enterprise-scaffold-1-0/04_test_spec.md`
- 保留并继续作为总览文档：
  - `docs/enterprise-scaffold-assessment.md`
- 更新决策记录：
  - `docs/decisions/AI_CHANGELOG.md`

- 后端目标改造范围：
  - `backend/app/api/main.py`
  - `backend/app/core/*`
  - `backend/app/infra/*`
  - `backend/app/modules/iam/*`
  - `backend/app/modules/system/*`
  - `backend/app/modules/audit/*`
  - `backend/app/modules/file/*`
  - `backend/app/modules/users/*`
  - `backend/app/modules/items/*`
  - `backend/app/modules/docs/*`

- 前端目标改造范围：
  - `frontend/src/app/*`
  - `frontend/src/platform/auth/*`
  - `frontend/src/platform/system/*`
  - `frontend/src/platform/docs/*`
  - `frontend/src/platform/audit/*`
  - `frontend/src/platform/file/*`
  - `frontend/src/features/items/*`
  - `frontend/src/shared/*`
  - `frontend/src/routes/*`

## Data Changes
- 批次 0：
  - 无强制数据库变更，先建立目录骨架与异常 / 日志 / trace 基线。
- 批次 1：
  - 新增 RBAC 相关表或模型：`Role`、`Permission`、`UserRole`、`RolePermission`。
- 批次 2：
  - 新增系统管理相关表或模型：`Department`、`DictType`、`DictItem`、`SystemParam`。
- 批次 3：
  - 新增审计日志与文件元数据相关表或模型：`AuditLog`、`OperationLog`、`FileObject`、`FileRelation`。
- 批次 4：
  - 以目录迁移和模块归属调整为主，不应再引入大范围无关数据结构变更。

## Core Flow (Pseudo)
1. 批次 0 先建立后端 `core / infra / modules` 与前端 `app / platform / features / shared` 骨架。
2. 抽出统一异常、日志、trace 和路由注册机制，为新模块进入平台提供稳定入口。
3. 批次 1 落 IAM / RBAC：后端提供角色、权限点、当前用户权限集合接口；前端接入页面守卫、菜单权限与按钮权限。
4. 批次 2 落系统管理：把当前 `Admin` 升级为 `system/users`，并扩展角色、部门、字典、参数模块。
5. 批次 3 落审计日志与文件中心：让关键写操作统一可追踪，让业务附件能力开始复用平台。
6. 批次 4 把现有 `users/items/docs` 迁成标准模块样板，冻结老的平铺式目录继续接新业务。
7. 每批结束后执行 OpenAPI / generated client / 页面导航 / 权限回归验证。

## Validation & Errors
- 批次 0 必须先建立统一异常结构，后续新增模块不允许各自定义不一致错误格式。
- 批次 1 后，任何新增平台页面不得再依赖 `is_superuser` 作为唯一授权方式。
- 批次 2 后，系统管理数据必须通过统一模块接口暴露，不允许新业务直接旁路读写字典或参数。
- 批次 3 后，涉及附件或关键写操作的新功能必须优先接入文件中心与审计日志，而不是局部重复实现。
- 批次 4 迁移时必须保证接口契约稳定，避免因为目录变更造成前端 client 或现有页面失效。

## Execution Plan
- Step 1: 将当前总览文档沉淀为独立 spec，形成 `docs/specs/enterprise-scaffold-1-0/01~04`。
- Step 2: 批次 0 实施结构骨架与治理基线。
- Step 3: 批次 1 实施 IAM / RBAC 最小闭环。
- Step 4: 批次 2 实施系统管理最小闭环。
- Step 5: 批次 3 实施审计日志、文件中心、统一治理能力。
- Step 6: 批次 4 把现有 `users/items/docs` 迁为标准样板模块。
- Step 7: 每批更新 `AI_CHANGELOG.md` 与对应细分 spec，避免蓝图与代码漂移。

## Rollback
- 文档层回滚：移除 `docs/specs/enterprise-scaffold-1-0/` 即可，但不建议，因为这会丢失明确实施依据。
- 批次化回滚：每个批次单独合并、单独验收，若出现问题，只回滚当前批次，不牵连未开始的后续批次。
- 结构迁移回滚：在现有 `users/items/docs` 未完全移除前，保持兼容入口，以减少一次性迁移失败风险。
- 权限与系统管理回滚：若 RBAC 或系统管理出现阻塞，可保留原有超管兜底路径作为短期 fallback，但不应作为长期终态。
