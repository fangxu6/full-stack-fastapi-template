# Requirement Spec

## Background
- 当前仓库已经具备 `FastAPI + SQLModel + PostgreSQL + React + TanStack Router/Query + generated client` 的完整工程基础，适合作为企业研发脚手架起点。
- 但现有结构仍偏模板项目：后端以 `api/routes + services + crud + models + schemas` 的全局技术分层为主，前端以 `routes + components + hooks` 的页面集合为主，权限模型也仍以 `is_superuser` 为中心。
- 如果后续要承接多个企业业务模块，这种平铺叠加方式会在权限、日志、文件、组织结构、工作流、菜单治理、前后端边界等方面迅速失控，因此需要先把仓库升级为“模块化单体”的企业平台底座。

## Goals
- 将当前仓库从模板型项目升级为可承接多个业务域的模块化企业脚手架。
- 建立清晰的后端 `core / infra / modules` 边界与前端 `app / platform / features / shared` 边界。
- 用批次化实施方式逐步落地 IAM / RBAC、系统管理、审计日志、文件中心、统一异常与可观测性治理。
- 保持现有 OpenAPI + generated client 的契约式协作优势，不通过大爆炸式重构破坏现有可运行能力。

## Scope
- In scope:
  - 定义企业脚手架 1.0 的目标架构、目录结构、模块边界与迁移原则。
  - 规划后端模块化目录：`modules/iam`、`modules/system`、`modules/audit`、`modules/file`、`modules/users`、`modules/items`、`modules/docs`。
  - 规划前端模块化目录：`app`、`platform/auth`、`platform/system`、`platform/docs`、`platform/audit`、`platform/file`、`features/items`、`shared/*`。
  - 明确首批平台模块：IAM / RBAC、系统管理、审计日志、文件中心、异常 / 日志 / trace 体系、前端权限守卫与导航治理。
  - 按批次拆分实施计划、测试重点、验收方式和输出物要求。
- Out of scope:
  - 一次性完成全部代码迁移。
  - 直接拆分为微服务。
  - 在本阶段引入完整 BPMN、报表平台、多租户 SaaS 完整能力。
  - 立即替换全部现有 `users/items/docs` 模块实现。
  - 修改生成代码目录 `frontend/src/client/**` 的手工组织方式。

## Acceptance Criteria
- AC1: 在 `docs/specs/enterprise-scaffold-1-0/` 下形成完整的 `01~04` 规范文档，可独立指导后续实施。
- AC2: 文档明确给出当前结构到目标结构的演进方向，并说明为什么必须优先走模块化单体而非微服务。
- AC3: 文档明确首批批次化实施顺序，至少覆盖结构骨架、IAM / RBAC、系统管理、审计日志、文件中心、现有模块样板迁移。
- AC4: 文档明确后端与前端的目录职责边界、模块归属、关键页面/组件/路由迁移方向。
- AC5: 文档明确实施过程中的契约约束：OpenAPI 为主边界、前端使用 generated client、老模块允许增量迁移而非一次性重写。
- AC6: 文档包含可验证的测试和验收策略，而不是只有抽象建议。

## Constraints
- 必须遵守当前仓库的文档驱动流程：`01_requirement.md -> 02_interface.md -> 03_implementation.md -> 04_test_spec.md -> code -> AI_CHANGELOG.md`。
- 必须保持现有系统在迁移过程中的可运行性，不能以大规模目录移动换取表面整洁。
- 前后端边界必须继续以 OpenAPI 为准，前端不得退回为散乱手写请求。
- 不直接编辑 `frontend/src/client/**` 和 `frontend/src/routeTree.gen.ts`。
- 任何新模块设计都必须优先考虑复用性、权限接入、日志接入、文件接入和后续可拆分性。

## Risks & Rollout
- 文档本身只是实施蓝图，不代表代码已经完成迁移；如果后续执行不持续同步文档，规范会快速过期。
- 批次划分是基于当前仓库现状的推荐顺序，若实际业务优先级变化，顺序可能需要调整，但模块边界原则不应轻易退化。
- 若先做业务、后补底座，平台化改造会不断被打断；因此建议优先完成批次 0 和批次 1，再接新业务模块。
- 回滚策略以“增量落地、逐批合并”为主：每批改动都应可单独验收、单独回退，而不是形成一个长期悬而未决的大分支。
