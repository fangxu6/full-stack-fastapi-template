# Test Spec

## Scope
- Covered layers: 文档规范完整性、后端结构治理、权限契约、系统管理接口、审计与文件中心、前端路由/菜单/页面接入、OpenAPI 契约与 generated client 回归。

## Strategy
- 先验证文档是否足以独立指导实施，再按批次验证结构改造是否真正落地。
- 每个批次都应同时覆盖：
  - 后端接口或结构基线
  - 前端页面或导航接入
  - OpenAPI 与 generated client 边界
  - 权限与错误返回回归
- 迁移类批次重点关注“目录变了，但能力没坏”；治理类批次重点关注“规则统一了，而不是多了一套并行实现”。

## Test Cases
- TC1: `docs/specs/enterprise-scaffold-1-0/` 下存在完整 `01~04` 文档，内容与 `docs/enterprise-scaffold-assessment.md` 保持一致方向，不互相冲突。
- TC2: 批次 0 完成后，后端存在统一异常 / 日志 / trace 基线，前端存在 `app / platform / shared` 基础骨架，且现有页面仍可访问。
- TC3: 批次 1 完成后，后端可返回当前用户权限集合，前端菜单、页面守卫、按钮权限不再只依赖 `is_superuser`。
- TC4: 批次 2 完成后，系统管理模块至少覆盖用户、角色、部门、字典、参数中的核心 CRUD 或查询能力。
- TC5: 批次 3 完成后，关键写操作可落审计日志，附件上传与文件列表可通过统一文件中心完成。
- TC6: 批次 4 完成后，`users/items/docs` 至少有 2 到 3 个模块按新目录结构完整跑通，且 OpenAPI client 与现有页面不回退。
- TC7: 每个批次完成后，`AI_CHANGELOG.md` 与相应 spec 都有同步更新，不出现“代码已改、文档仍旧”的漂移。
- TC8: 新增平台接口命名空间遵循 `iam / system / audit / files` 等分域约定，而不是继续堆入全局平铺 routes。

## Data Setup
- 以当前仓库现有 `users`、`items`、`docs/rules` 为迁移和回归基准样本。
- RBAC 测试需要至少准备：
  - 一个超管用户
  - 一个普通用户
  - 一个具备部分权限点的角色用户
- 系统管理测试需要准备基础字典、参数、部门、角色样本数据。
- 文件中心测试需要准备至少一个可上传文件与一个带 `business_type + business_id` 的关联场景。
- 审计日志测试需要准备至少一个关键写操作样本，例如用户更新、角色授权或 Item 修改。

## Regression Notes
- 后端从 `services/crud/routes` 向 `modules/*` 迁移时，最容易引发导入边界、路由注册顺序和 OpenAPI 契约漂移，需要重点回归。
- 前端从 `routes/components/hooks` 向 `app/platform/features/shared` 迁移时，最容易引发路由壳过重、Query Key 漂移和菜单权限退化，需要重点回归。
- IAM / RBAC 落地过程中，短期最容易出现“菜单隐藏了但接口仍可访问”或“接口收紧了但前端未同步提示”的前后端不一致问题。
- 文件中心与审计日志落地后，需特别关注是否出现新的重复上传实现或绕过平台日志的写操作分支。
