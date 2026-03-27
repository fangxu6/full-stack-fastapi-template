# 前端 CRUD 开发模板

## 1. 用途

本模板用于指导当前仓库内的**常规 CRUD 页面**开发。

- 适用场景：列表页 + 创建 + 编辑 + 删除 + 基本权限控制 + 标准空态/加载态/错误态。
- 典型参考：`items`、`admin/users`。
- 使用方式：
  - 通用原则先遵循 [前端开发规范](D:/Workspace/full-stack-fastapi-template/docs/rules/前端开发规范.md)
  - 如果是常规 CRUD 页面，再直接参照本模板落地代码结构和交互模式

本模板的目标不是覆盖所有页面，而是把高频 CRUD 路径固定下来，让新页面默认长成同一种样子。

## 2. 标准目录结构

新增一个常规 CRUD 页面时，优先按下面的结构组织：

```text
frontend/src/routes/_layout/<resource>.tsx
frontend/src/components/<Resource>/Add<Resource>.tsx
frontend/src/components/<Resource>/Edit<Resource>.tsx
frontend/src/components/<Resource>/Delete<Resource>.tsx
frontend/src/components/<Resource>/<Resource>ActionsMenu.tsx
frontend/src/components/<Resource>/columns.tsx
frontend/src/components/Pending/Pending<Resources>.tsx
```

说明：

- `route` 文件负责页面装配和数据边界。
- `columns.tsx` 负责表格列定义，不把列定义塞回页面文件。
- `Add/Edit/Delete` 各自独立，避免一个大组件同时处理所有弹窗逻辑。
- `ActionsMenu` 负责把编辑、删除操作挂到表格行上。
- `Pending...` 负责和当前表格结构对应的骨架屏。

## 3. 页面骨架模板

标准 CRUD 页面应接近下面这种结构：

```tsx
import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Suspense } from "react"

import { ResourceService } from "@/client"
import AddResource from "@/components/Resource/AddResource"
import { DataTable } from "@/components/Common/DataTable"
import PendingResources from "@/components/Pending/PendingResources"
import { columns } from "@/components/Resource/columns"

function getResourcesQueryOptions() {
  return {
    queryKey: ["resources"],
    queryFn: () => ResourceService.readResources({ skip: 0, limit: 100 }),
  }
}

export const Route = createFileRoute("/_layout/resources")({
  component: ResourcesPage,
  head: () => ({
    meta: [{ title: "Resources - FastAPI Template" }],
  }),
})

function ResourcesTableContent() {
  const { data } = useSuspenseQuery(getResourcesQueryOptions())

  if (data.data.length === 0) {
    return <ResourceEmptyState />
  }

  return <DataTable columns={columns} data={data.data} />
}

function ResourcesTable() {
  return (
    <Suspense fallback={<PendingResources />}>
      <ResourcesTableContent />
    </Suspense>
  )
}

function ResourcesPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Resources</h1>
          <p className="text-muted-foreground">Create and manage resources</p>
        </div>
        <AddResource />
      </div>
      <ResourcesTable />
    </div>
  )
}
```

固定规则：

- 页面标题区始终包含 `h1` 和一句简短说明。
- 主操作按钮默认放右上角。
- 列表本体通过 `Suspense` 包裹。
- 查询函数提取为 `getResourcesQueryOptions()` 这类 helper，避免直接把请求细节写进 JSX。

## 4. 路由文件职责

路由文件只做这些事：

- 定义 `Route`
- 配置 `head()`
- 在需要时添加 `beforeLoad` 鉴权或权限拦截
- 拼页面结构
- 决定加载态、空态和错误态的边界

路由文件不要做这些事：

- 不内联很长的列定义
- 不内联新增/编辑/删除弹窗实现
- 不在 JSX 中直接写请求细节
- 不把通用格式化或业务转换散落在页面中

## 5. Query Key 与查询约定

建议固定如下命名：

- 列表：`["items"]`、`["users"]`
- 当前用户：`["currentUser"]`
- 单资源详情：`["items", itemId]`

常规规则：

- 同一资源列表使用同一个基础 key。
- 新增、编辑、删除成功后，默认失效该资源的列表 key。
- 优先精确失效，例如：

```tsx
queryClient.invalidateQueries({ queryKey: ["items"] })
```

避免把常规 CRUD 默认写成全局失效：

```tsx
queryClient.invalidateQueries()
```

除非这次变更确实会影响多个资源的缓存。

## 6. 表格列模板

`columns.tsx` 负责：

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
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span className="text-muted-foreground">
        {row.original.description || "No description"}
      </span>
    ),
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

- `actions` 列放最后。
- 空值要显示友好文案，不留空白。
- 格式化逻辑保持轻量；复杂逻辑提取为小组件。

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
5. `onError` 中复用 `handleError.bind(showErrorToast)`
6. `onSettled` 中失效对应列表 key

新增组件适合用 `DialogTrigger asChild` 绑定“Add”按钮。

## 8. 编辑弹窗模板

编辑弹窗和新增弹窗保持相同结构，但有两个固定差异：

- `defaultValues` 来自当前行数据
- 提交体只包含允许更新的字段

建议保留 `onSuccess` 回调，供调用方在需要时做额外收尾，但列表刷新仍由组件自身负责。

编辑组件适合挂在 `DropdownMenuItem` 上，通过操作菜单触发。

## 9. 删除确认模板

删除操作默认用确认弹窗，不直接删除。

标准结构：

- `DropdownMenuItem variant="destructive"` 作为入口
- 弹窗内给出不可逆提示
- 提供 `Cancel` 和 `Delete` 两个按钮
- 删除按钮用 `LoadingButton variant="destructive"`

固定规则：

- 删除成功后给 toast 并关闭弹窗。
- 删除后默认失效对应资源列表。
- 删除说明要明确告知是否会联动删除关联数据。

## 10. Actions Menu 模板

常规表格行操作统一收敛到 `ActionsMenu`：

- 编辑
- 删除
- 必要时补充复制 ID、查看详情等动作

这样可以避免：

- 每个 `columns.tsx` 重复拼动作按钮
- 每一行出现过多裸露按钮
- 不同资源的操作入口样式不一致

## 11. 加载态、空态、错误态模板

### 11.1 加载态

默认使用和表格列结构一致的 `Pending<Resource>s` 骨架组件。

固定要求：

- 列头与正式表格对齐
- 骨架数量固定 4 到 6 行即可
- 操作列也要给占位，避免布局跳动

### 11.2 空态

空态至少包含：

- 一个简洁图标或视觉占位
- 一句状态说明
- 一句下一步提示
- 如适合，保留“新增”主操作入口

### 11.3 错误态

默认复用全局错误边界；如果页面内需要局部错误提示，也要满足：

- 面向用户描述结果
- 提供“返回”“重试”或其他下一步动作
- 不直接暴露原始异常对象

## 12. 表单字段约定

常规 CRUD 表单统一遵循：

- Schema 先行
- 类型从 schema 推导
- `mode: "onBlur"`
- `criteriaMode: "all"`
- `defaultValues` 完整声明
- 必填项在标签上显式标出
- 错误提示通过 `FormMessage` 展示

如果有确认密码、条件字段、可选密码等场景，统一在 schema 层做约束，不把规则散落到提交函数里。

## 13. 成功与失败反馈

常规 CRUD 的反馈模式固定如下：

- 创建成功：toast + 关闭弹窗 + 重置表单 + 刷新列表
- 编辑成功：toast + 关闭弹窗 + 刷新列表
- 删除成功：toast + 关闭弹窗 + 刷新列表
- 失败：统一走 `showErrorToast`

不要这样做：

- 成功后无提示
- 失败只打印控制台
- 同一资源的不同弹窗使用不同的反馈语气和流程

## 14. 推荐开发顺序

开发一个新的常规 CRUD 页面时，建议按这个顺序：

1. 确认后端 OpenAPI 已稳定，必要时先生成 client
2. 创建路由页面文件
3. 创建 `columns.tsx`
4. 创建 `Pending<Resource>s.tsx`
5. 创建 `Add<Resource>.tsx`
6. 创建 `Edit<Resource>.tsx`
7. 创建 `Delete<Resource>.tsx`
8. 创建 `ActionsMenu`
9. 回到路由页接线和空态处理
10. 运行 lint / build / 关键路径测试

## 15. 常规 CRUD 页面自检清单

- 是否使用了标准目录结构。
- 是否把请求逻辑收敛到 query/mutation，而不是写在 JSX 中。
- 是否有 `Pending`、空态、错误态。
- 是否把 `actions` 列放在最后。
- 是否新增了 `Add/Edit/Delete` 三类标准组件中的对应项。
- 是否使用生成客户端而不是手写 URL。
- 是否精确失效了资源列表 key。
- 是否所有提交按钮都有 loading 状态。
- 是否成功和失败都有统一 toast。
- 是否运行了 `bun run lint`。

## 16. 不适用场景

以下场景不要强行套这个模板：

- 多步骤表单
- 重度筛选、分组、批量操作页面
- 含复杂拖拽、实时协作或看板交互的页面
- 需要独立详情页、子资源嵌套操作的大型模块

这些场景仍然遵循 [前端开发规范](D:/Workspace/full-stack-fastapi-template/docs/rules/前端开发规范.md)，但应单独设计页面结构。

## 17. 模板依据

本模板主要基于以下现有代码模式整理：

- `frontend/src/routes/_layout/items.tsx`
- `frontend/src/routes/_layout/admin.tsx`
- `frontend/src/components/Items/AddItem.tsx`
- `frontend/src/components/Items/EditItem.tsx`
- `frontend/src/components/Items/DeleteItem.tsx`
- `frontend/src/components/Items/columns.tsx`
- `frontend/src/components/Admin/AddUser.tsx`
- `frontend/src/components/Admin/EditUser.tsx`
- `frontend/src/components/Admin/DeleteUser.tsx`
- `frontend/src/components/Common/DataTable.tsx`
- `frontend/src/components/Pending/PendingItems.tsx`
