# Implementation Spec - Backend 重构补档

## Goal Summary
- 已将 backend 主体重构为清晰分层架构，路由层不再承载核心业务逻辑。
- 新增 service 层承接业务编排，crud 层专注原子数据库操作；`items` 暂时保持轻量 CRUD 结构。
- 将依赖注入拆分为独立模块，将 API DTO 提取到 schemas 层。
- 同步补齐架构与开发规范文档，确保后续开发一致性。

## File Changes
- 架构与文档：`backend/ARCHITECTURE.md`、`backend/CODING_STANDARDS.md`、`backend/README.md`
- 依赖注入：`backend/app/api/dependencies/__init__.py`、`backend/app/api/dependencies/auth.py`、`backend/app/api/dependencies/database.py`、`backend/app/api/deps.py`
- 路由层：`backend/app/api/routes/users.py`、`backend/app/api/routes/login.py`、`backend/app/api/routes/items.py`
- 服务层：`backend/app/services/__init__.py`、`backend/app/services/user.py`、`backend/app/services/auth.py`、`backend/app/services/item.py`
- 持久化与模型：`backend/app/crud/*.py`、`backend/app/models/*.py`
- DTO 契约：`backend/app/schemas/__init__.py`、`backend/app/schemas/user.py`、`backend/app/schemas/item.py`、`backend/app/schemas/security.py`

## Data Changes
- 无业务性数据库结构变更要求。
- 本次重点是代码组织和职责迁移，不涉及新增迁移脚本。

## Core Flow (After Refactor)
1. Route 接收请求并解析参数。
2. Route 注入依赖并调用对应 Service。
3. Service 校验规则并协调一个或多个 CRUD 或模块 repository 操作。
4. CRUD/repository 与数据库交互，返回模型数据。
5. Service 组装业务结果，Route 输出响应模型。

## Validation & Errors
- 输入校验由 `schemas/` 与 FastAPI 参数体系承担。
- 业务校验与权限判断下沉到 Service。
- HTTP 异常由 Route 进行最终状态码映射，错误语义保持兼容。

## Execution Trace (Completed)
- Step 1: 模块化 models 与 CRUD（打散集中定义，按领域拆分）。
- Step 2: 引入 service 层并将 users/login/items 业务逻辑迁移。
- Step 3: 增加 schema 层作为 API DTO 契约。
- Step 4: 重构依赖注入为 `api/dependencies/` 子模块。
- Step 5: 更新架构与代码规范文档，固化团队约束。
- Step 6: 根据 ORM 隔离与实用边界规则，items 保持 `/api/v1/items/*` 与 `router -> service -> crud -> ORM` 轻量链路。

## Rollback
- 若需回滚，按提交顺序逆向回退：
  1) 文档与规范更新；
  2) 依赖注入模块化；
  3) schema 层引入；
  4) service 层迁移；
  5) models/crud 拆分。
