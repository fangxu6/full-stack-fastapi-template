# Implementation Spec - 前端 CRUD 开发模板

## Goal Summary
- 把当前项目中最典型的 CRUD 实现方式整理为模板文档，供后续功能开发直接套用。

## Planned Changes
- 新增规格目录 `docs/specs/frontend-crud-template/`。
- 新增 `docs/rules/前端 CRUD 开发模板.md`。
- 更新 `docs/rules/前端开发规范.md`，增加对 CRUD 模板的引用。
- 更新 `docs/decisions/AI_CHANGELOG.md`，记录本次决策。

## Template Basis
- 页面装配与 Suspense 边界：来自 `routes/_layout/items.tsx` 和 `routes/_layout/admin.tsx`
- 列定义与操作菜单：来自 `components/Items/columns.tsx` 和 `components/Admin/columns.tsx`
- 新增 / 编辑 / 删除弹窗：来自 `components/Items/*` 与 `components/Admin/*`
- 列表容器：来自 `components/Common/DataTable.tsx`
- Pending 骨架：来自 `components/Pending/*`

## Non-Goals
- 不产出自动生成 CRUD 文件的脚本。
- 不重写现有 CRUD 页面实现。
- 不定义复杂查询表单、批量操作、导入导出等增强场景模板。
