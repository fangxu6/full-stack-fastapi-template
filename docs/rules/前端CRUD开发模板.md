# 前端 CRUD 开发模板

## 1. 用途

本模板用于指导当前仓库内的常规 CRUD 页面开发。

- 适用场景：列表页 + 创建 + 编辑 + 删除 + 基本权限控制 + 标准空态/加载态/错误态
- 典型参考：`features/items`、`platform/system`
- 使用方式：
  - 通用原则先遵循 [前端开发规范](D:/Workspace/full-stack-fastapi-template/docs/rules/前端开发规范.md)
  - 如果是常规 CRUD 页面，再直接参照本模板落地代码结构和交互模式

本模板的目标不是覆盖所有页面，而是把高频 CRUD 路径固定下来，让新页面默认长成与当前架构一致的样子。

## 2. 当前推荐目录结构

新增一个常规 CRUD 页面时，优先按下面的结构组织。

### 如果它是业务功能

```text
frontend/src/routes/_layout/<resource>.tsx
frontend/src/features/<resource>/
├── pages/<Resource>Page.tsx
├── components/
│   ├── Add<Resource>Dialog.tsx
│   ├── Edit<Resource>MenuItem.tsx
│   ├── Delete<Resource>MenuItem.tsx
│   ├── <Resource>ActionsMenu.tsx
│   └── <resource>-columns.tsx
```

### 如果它是平台能力

```text
frontend/src/routes/_layout/<resource>.tsx
frontend/src/platform/<domain>/
├── pages/<Resource>Page.tsx
├── components/<resource>/
│   ├── Add<Resource>Dialog.tsx
│   ├── Edit<Resource>MenuItem.tsx
│   ├── Delete<Resource>MenuItem.tsx
│   ├── <Resource>ActionsMenu.tsx
│   └── <resource>-columns.tsx
```

共享层通常只放：

- `shared/components/table/*`
- `shared/components/feedback/*`
- `shared/components/layout/*`

不要再为 CRUD 页面新增：

- `frontend/src/components/<Resource>/*`
- `frontend/src/components/Common/*`

## 3. 路由文件职责

路由文件只做这些事：

- 定义 `Route`
- 配置 `head()`
- 在需要时添加 `beforeLoad`
- 引用真实页面模块

路由文件不要做这些事：

- 不内联完整页面实现
- 不内联很长的列定义
- 不内联新增/编辑/删除弹窗实现
- 不在 JSX 中直接写请求细节

当前目标是“薄路由文件”。

## 4. 页面骨架模板

标准 CRUD 页面应接近下面这种结构：

```tsx
import { useSuspenseQuery } from "@tanstack/react-query"
import { Suspense } from "react"

import { ResourceService } from "@/client"
import { DataTable } from "@/shared/components/table"
import { ItemsTableSkeleton } from "@/shared/components/feedback"
import { AddResourceDialog } from "../components/AddResourceDialog"
import { columns } from "../components/resource-columns"

function getResourcesQueryOptions() {
  return {
    queryKey: ["resources"],
    queryFn: () => ResourceService.readResources({ skip: 0, limit: 100 }),
  }
}

function ResourcesTableContent() {
  const { data } = useSuspenseQuery(getResourcesQueryOptions())

  if (data.data.length === 0) {
    return <ResourceEmptyState />
  }

  return <DataTable columns={columns} data={data.data} />
}

export function ResourcesPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Resources</h1>
          <p className="text-muted-foreground">Create and manage resources</p>
        </div>
        <AddResourceDialog />
      </div>

      <Suspense fallback={<ItemsTableSkeleton />}>
        <ResourcesTableContent />
      </Suspense>
    </div>
  )
}
```

固定规则：

- 页面标题区始终包含 `h1` 和一句简短说明
- 主操作按钮默认放右上角
- 列表本体通过 `Suspense` 包裹
- 查询函数提取为 `getResourcesQueryOptions()` 这类 helper

## 5. Query Key 与查询约定

建议固定如下命名：

- 列表：`["items"]`、`["users"]`
- 当前用户：`["currentUser"]`
- 单资源详情：`["items", itemId]`

常规规则：

- 同一资源列表使用同一个基础 key
- 新增、编辑、删除成功后，默认失效该资源的列表 key
- 优先精确失效，例如：

```tsx
queryClient.invalidateQueries({ queryKey: ["items"] })
```

避免无差别：

```tsx
queryClient.invalidateQueries()
```

## 6. 表格列模板

`<resource>-columns.tsx` 负责：

- 字段展示
- 简单格式化
- 空值显示
- 操作列挂载

标准骨架：

```tsx
import type { ColumnDef } from "@tanstack/react-table"

import type { ResourcePublic } from "@/client"
import { ResourceActionsMenu } from "./ResourceActionsMenu"

export const columns: ColumnDef<ResourcePublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ResourceActionsMenu resource={row.original} />
      </div>
    ),
  },
]
```

固定规则：

- `actions` 列放最后
- 空值要显示友好文案，不留空白
- 格式化逻辑保持轻量；复杂逻辑提取为小组件

## 7. 新增弹窗模板

新增弹窗默认使用：

- `Dialog`
- `react-hook-form`
- `zodResolver`
- `LoadingButton`
- 成功 toast + 关闭弹窗 + 重置表单 + 失效列表

标准流程：

1. 用 `useState` 控制弹窗开关
2. 用 `useForm` 声明 schema 和 `defaultValues`
3. 用 `useMutation` 调用生成客户端
4. `onSuccess` 中给成功反馈并关闭弹窗
5. `onError` 中复用统一错误 toast
6. `onSettled` 中失效对应列表 key

## 8. 编辑与删除模板

### 编辑

- `defaultValues` 来自当前行数据
- 提交体只包含允许更新的字段
- 通常挂在 `ActionsMenu` 内触发

### 删除

- 默认用确认弹窗，不直接删除
- 入口通常是 `DropdownMenuItem variant="destructive"`
- 删除成功后给 toast、关闭弹窗、刷新列表

## 9. Actions Menu 模板

常规表格行操作统一收敛到 `ActionsMenu`：

- 编辑
- 删除
- 必要时补充复制 ID、查看详情等动作

这样可以避免：

- 每个列定义文件重复拼动作按钮
- 每一行出现过多裸露按钮
- 不同资源的操作入口样式不一致

## 10. 加载态、空态、错误态模板

### 10.1 加载态

优先复用与当前表格结构对应的共享或域内 skeleton。

例如：

- `shared/components/feedback/ItemsTableSkeleton.tsx`
- `shared/components/feedback/UsersTableSkeleton.tsx`

### 10.2 空态

空态至少包含：

- 一句状态说明
- 一句下一步提示
- 如适合，保留“新增”主操作入口

### 10.3 错误态

优先复用当前共享错误态模式：

- 根级：`ErrorState` / `NotFoundState`
- 页面局部：面向用户的错误提示 + 下一步动作

## 11. 成功与失败反馈

常规 CRUD 的反馈模式固定如下：

- 创建成功：toast + 关闭弹窗 + 重置表单 + 刷新列表
- 编辑成功：toast + 关闭弹窗 + 刷新列表
- 删除成功：toast + 关闭弹窗 + 刷新列表
- 失败：统一走共享错误处理或共享 toast 入口

## 12. 推荐开发顺序

开发一个新的常规 CRUD 页面时，建议按这个顺序：

1. 确认它属于 `platform` 还是 `features`
2. 确认后端 OpenAPI 已稳定，必要时先生成 client
3. 创建页面模块 `pages/<Resource>Page.tsx`
4. 创建 `<resource>-columns.tsx`
5. 创建 `Add<Resource>Dialog.tsx`
6. 创建 `Edit<Resource>MenuItem.tsx`
7. 创建 `Delete<Resource>MenuItem.tsx`
8. 创建 `<Resource>ActionsMenu.tsx`
9. 创建或复用 skeleton / 空态 / 错误态
10. 创建薄路由文件接线
11. 运行 lint / build / 关键路径测试

## 13. 常规 CRUD 页面自检清单

- 是否先判断了它属于 `platform` 还是 `features`
- 是否把页面实现放进了 `pages/*`，而不是塞回 `routes/*`
- 是否没有新增 `components/Common/*` 或 `components/<Resource>/*` 旧结构
- 是否把请求逻辑收敛到 query/mutation，而不是写在 JSX 中
- 是否有加载态、空态、错误态
- 是否把 `actions` 列放在最后
- 是否使用生成客户端而不是手写 URL
- 是否精确失效了资源列表 key
- 是否所有提交按钮都有 loading 状态
- 是否运行了 `bun run lint`

## 14. 不适用场景

以下场景不要强行套这个模板：

- 多步骤表单
- 重度筛选、分组、批量操作页面
- 含复杂拖拽、实时协作或看板交互的页面
- 需要独立详情页、子资源嵌套操作的大型模块

这些场景仍然遵循 [前端开发规范](D:/Workspace/full-stack-fastapi-template/docs/rules/前端开发规范.md)，但应单独设计页面结构。

## 15. 模板依据

本模板主要基于以下现有代码模式整理：

- `frontend/src/routes/_layout/items.tsx`
- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/features/items/pages/ItemsPage.tsx`
- `frontend/src/features/items/components/AddItemDialog.tsx`
- `frontend/src/features/items/components/EditItemMenuItem.tsx`
- `frontend/src/features/items/components/DeleteItemMenuItem.tsx`
- `frontend/src/features/items/components/ItemActionsMenu.tsx`
- `frontend/src/features/items/components/item-columns.tsx`
- `frontend/src/platform/system/pages/AdminUsersPage.tsx`
- `frontend/src/platform/system/components/users/AddUserDialog.tsx`
- `frontend/src/platform/system/components/users/EditUserMenuItem.tsx`
- `frontend/src/platform/system/components/users/DeleteUserMenuItem.tsx`
- `frontend/src/platform/system/components/users/UserActionsMenu.tsx`
- `frontend/src/platform/system/components/users/user-columns.tsx`
- `frontend/src/shared/components/table/DataTable.tsx`
- `frontend/src/shared/components/feedback/ItemsTableSkeleton.tsx`
- `frontend/src/shared/components/feedback/UsersTableSkeleton.tsx`
