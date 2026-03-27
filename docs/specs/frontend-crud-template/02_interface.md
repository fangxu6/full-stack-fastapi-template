# Interface Spec - 前端 CRUD 开发模板

## Overview
- 本次交付为文档模板，不引入新的运行时代码接口。

## Output Contract

### New Document
- `docs/rules/前端 CRUD 开发模板.md`
- 内容类型：中文 Markdown
- 使用场景：新增常规 CRUD 页面时作为直接参照模板

### Document Sections
- 适用范围与使用方式
- 标准目录结构
- 列表页路由模板
- `columns.tsx` 模板
- 新增 / 编辑 / 删除组件模板
- 加载态、空态、错误态模板
- query key 与 invalidate 规范
- CRUD 页面自检清单

## Integration With Existing Docs
- `docs/rules/前端开发规范.md`：定义通用原则
- `docs/rules/前端 CRUD 开发模板.md`：定义常规 CRUD 的标准落地方式

## Referenced Source Files
- `frontend/src/routes/_layout/items.tsx`
- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/components/Items/*`
- `frontend/src/components/Admin/*`
- `frontend/src/components/Common/DataTable.tsx`
- `frontend/src/components/Pending/*`
