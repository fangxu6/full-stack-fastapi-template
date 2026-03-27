# Implementation Spec - 前端开发规范

## Goal Summary
- 在不改动前端运行时代码的前提下，把当前已成立的前端开发方式固化成规范文档，并补齐 React 性能最佳实践层面的明确约束。

## Planned Changes
- 新增功能规格目录 `docs/specs/frontend-development-standards/`，记录本次文档化的需求、接口、实施与测试范围。
- 更新 `docs/rules/前端开发规范.md`，作为后续前端开发的主规范，并显式纳入 `.agents/skills/react-best-practices/` 的适配规则。
- 更新 `docs/decisions/AI_CHANGELOG.md`，记录本次规则沉淀和性能规范增强的决策与原因。

## Content Strategy
- 先写“现有约定”，确保规范与现有代码可对齐。
- 再写“增强要求”，补充对后续开发有高收益、低冲突的强约束。
- 对 `.agents/skills/react-best-practices/` 的 12 条规则做项目化转译：
  - 保留适用于 Vite + React 19 + TanStack Query 的规则。
  - 避免照搬与当前栈不匹配的框架专属写法。
  - 将性能规则落到“什么时候必须做、什么时候不必机械套用”的可执行表述。
- 每个关键部分尽量使用当前代码中的具体模式表达，例如：
  - Provider 与全局异常处理来自 `main.tsx`
  - 鉴权与路由守卫来自 `routes/_layout.tsx` 和 `hooks/useAuth.ts`
  - 表单模式来自 `routes/login.tsx` 与 `components/Items/AddItem.tsx`
  - 通用列表模式来自 `components/Common/DataTable.tsx`
  - 主题与样式变量来自 `index.css`

## Non-Goals
- 不创建代码生成脚本。
- 不自动修正现有代码风格差异。
- 不把规范扩展为跨前后端总规范。
