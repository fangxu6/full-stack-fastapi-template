# Requirement Spec - 前端 CRUD 开发模板

## Background
- 当前前端后续开发将以常规 CRUD 页面为主，例如列表、创建、编辑、删除、空态和权限控制。
- 虽然仓库已有前端开发规范，但常规 CRUD 仍需要一份更具体的页面模板，减少重复设计和实现分歧。

## Goals
- 基于现有 `items` 和 `admin/users` 实现，沉淀一份可复用的 CRUD 开发模板。
- 固定常规 CRUD 的页面结构、组件拆分、查询刷新、表单和反馈方式。
- 与已有 `docs/rules/前端开发规范.md` 配合使用，形成“原则 + 模板”的双层约束。

## Scope
- In scope:
  - 新增 `docs/rules/前端 CRUD 开发模板.md`
  - 明确典型 CRUD 页面目录结构与代码骨架
  - 明确列表、弹窗表单、空态、加载态、错误态、自检清单
- Out of scope:
  - 修改现有 CRUD 运行时代码
  - 生成脚手架命令或代码生成器
  - 覆盖复杂工作流页面、嵌套流程页面或多步骤表单

## Acceptance Criteria
- AC1: 模板内容能直接映射到当前 `items` 与 `admin/users` 的实现模式。
- AC2: 模板能指导新增常规 CRUD 页面在目录、状态处理和交互反馈上保持一致。
- AC3: 模板明确哪些是建议复用的标准文件，哪些是必须具备的状态与反馈。
- AC4: 模板文档与已有前端开发规范互相引用，职责边界清晰。

## Constraints
- 保持和当前技术栈一致：TanStack Router、React Query、React Hook Form、Zod、Tailwind、shadcn/ui。
- 不要求现有代码立即全面整改，优先约束后续新增或修改的 CRUD 页面。
