# 多角色绑定

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)  
> 复用定位：在 Vue 管理端把“当前用户拥有一个角色”升级为“用户拥有完整角色集合和权限并集”，并将其收敛到 Pinia 状态层。

## 提交信息

- 仓库：`JSE_UI_AI`
- SHA：`cda2ac7bc12d64f79586f3e88712f048bb0509fc`
- 日期：`2025-11-03 13:45:13 +0800`
- 父提交：`e786e644fad69c0b618308aff8caad3e5ac93a98`
- 作者：`hanqiang <240448317@qq.com>`
- 分类：前端：身份权限、基础数据与应用框架
- 原始主题：多角色绑定

## 这次提交解决的问题

前一版前端 RBAC 已具备角色、功能树和权限判断，但当前用户主要使用单值 `role`。它无法正确表达一个用户同时承担多个职责，例如同时拥有“采购审批”和“基础数据维护”角色：

- 页面若只读取 `role`，会遗漏其余角色带来的权限；
- 登录响应中的用户身份和运行时权限来自不同接口，前端没有统一合并位置；
- 菜单、路由和页面若各自处理角色数组，会产生不同的判断规则。

`cda2ac7b` 将合并逻辑集中在 `stores/user.ts:fetchUser()`：从权限汇总接口获得角色集合与权限集合，写入当前用户的 `roles`、`role_names` 和扁平权限映射，同时保留 `role` 作为旧代码可继续读取的兼容字段。

本次提交的实质功能变更只有两个文件：

| 文件 | 作用 |
| --- | --- |
| `src/services/auth.ts` | 定义 `UserPermissionSummary`，新增 `GET /users/permissions` 适配函数。 |
| `src/stores/user.ts` | 在 `fetchUser()` 中并发读取身份、旧权限映射和新权限汇总，统一写入用户状态。 |

提交中其它大量文件的差异为行尾格式变化，不能据此推断角色页面、路由或侧边栏在此提交中被重构。

## 原始跨端契约

新增的权限汇总接口为当前登录用户返回完整授权快照的一部分：

```ts
interface UserPermissionSummary {
  user_id: string
  permission_count: number
  permissions: string[]
  roles: Array<{
    RoleID: string
    RoleCode: string
    RoleName: string
  }>
}

async function getUserPermissionSummary(): Promise<UserPermissionSummary> {
  const response = await apiClient.get<UserPermissionSummary>('/users/permissions')
  return response.data
}
```

其中：

- `roles` 是用户有效角色的完整集合，`RoleCode` 是客户端判断使用的稳定值，`RoleName` 仅用于显示；
- `permissions` 是所有有效角色产生的 `FeatureKey` 去重并集，例如 `menu:roles`、`role:read:list`；
- `permission_count` 适合日志、监控和前后端排障，不应作为授权判断依据；
- 用户身份仍来自 `GET /auth/me`，权限汇总不能替代对 token 和用户状态的服务端校验。

原始 `User` 类型同时保留以下字段：

```ts
interface User {
  role: string
  roles?: string[]
  role_names?: string[]
  permissions?: UserPermissions | Record<string, boolean>
}
```

字段语义必须固定：

| 字段 | 语义 | 新代码是否应作为依据 |
| --- | --- | --- |
| `roles` | 完整角色编码集合 | 是，所有角色判断从这里或其规范化集合读取。 |
| `role_names` | 与角色对应的显示名称集合 | 仅展示。 |
| `role` | `roles[0]` 的主角色/兼容别名 | 否，不能据此计算权限或判断是否属于其它角色。 |
| `permissions` | 所有角色有效权限的并集 | 是，UI 权限判断唯一事实源。 |

角色顺序若业务上没有“主角色”概念，就不能把 `roles[0]` 当作有业务含义的优先级。保留 `role` 只是为了渐进迁移旧组件；新项目应直接使用 `roles`，需要主角色时让后端返回显式 `primary_role_code`。

## 原始状态合并流程

提交中的 `fetchUser()` 按以下顺序运行：

```text
login() / token 恢复后校验
          |
          v
GET /auth/me --------------------------> 用户身份 userData
          |
          +-- Promise.all ----------------------------------+
          |                                                 |
          v                                                 v
GET /auth/permissions                              GET /users/permissions
旧扁平权限映射                                       权限并集 + 完整角色列表
          |                                                 |
          +------------------- 合并 -------------------------+
                              |
                              v
{
  ...userData,
  permissions: { ...flatPerms, [summaryPermission]: true },
  roles: summary.roles.map(RoleCode),
  role_names: summary.roles.map(RoleName),
  role: roles[0] || userData.role || ''
}
                              |
                              v
Pinia user + localStorage.user_info
```

这样做有两个关键点：

1. 权限采用并集。不能根据 `role` 单值挑选权限，也不能让后一角色覆盖前一角色的权限。
2. 状态只在 store 写入。路由、侧边栏、指令和页面都消费 store 暴露的判断函数，不再各自调用权限接口或拼接角色逻辑。

`login()` 在拿到 token 和登录响应后调用 `fetchUser()`；`validateToken()` 同样通过它刷新登录态。登出或 token 校验失败必须同时清空内存用户、token 和本地身份/权限缓存，防止下一个用户短暂继承前一用户的菜单或操作权限。

## 角色与权限判断 API

`usePermission()` 是页面层的薄封装，真正的规范化和匹配都应留在 Pinia store：

```ts
const { hasRole, hasAnyRole, hasAllRoles } = usePermission()

hasRole('purchaser')
hasAnyRole(['purchaser', 'purchasing_manager'])
hasAllRoles(['quality_engineer', 'auditor'])
```

建议的规则如下：

- 角色编码比较大小写不敏感，并先去空值、去重；
- `hasAnyRole()` 为 OR，`hasAllRoles()` 为 AND；空数组应按 JavaScript 集合语义分别得到 `false` 和 `true`，调用方不应把空数组当作授权配置；
- 超级管理员短路是角色策略的一部分。当前项目以 `ADMIN` 为约定；迁移时应由服务端身份策略明确该编码和审计要求；
- `hasPermission()`、`hasAnyPermission()` 和 `hasAllPermissions()` 只读取权限并集。角色适合表达业务身份，权限键才适合表达可执行操作。

当前实现通过 `getNormalizedRoles()` 同时兼容旧 `role` 与新 `roles`，因此旧页面会继续工作。这个双读兼容层应有明确移除窗口；不能永久让两个字段都能被任意页面写入。

## 路由、导航与服务端边界

CodeGraph 显示 `usePermission()` 目前被约 162 个前端文件使用，`stores/user.ts` 还被认证组合式函数、应用启动、路由和侧边栏消费。因此不要在单个角色页面复制角色数组判断，所有调用应路由到 store。

```text
Pinia user.roles + user.permissions
          |
          v
usePermission() / hasPermission()
     |              |               |
     v              v               v
页面按钮          路由守卫          AppSidebar 菜单过滤
          \         |         /
           \--------+--------/
                    |
                    v
         后端 require_permission(...) 执行最终授权
```

当前路由守卫 `router/permissionGuard.ts` 根据路由 `meta.permissions`、`meta.anyPermissions` 和 `meta.featureKey` 组合判断；`AppSidebar.vue` 的 `hasMenuAccess()`、`hasModuleAccess()` 以相同 store 判断隐藏入口。这两层只改善体验，绝不是安全边界：用户可以直接输入 URL 或构造 HTTP 请求，所有受保护 API 仍必须在服务端以 `require_permission(...)` 等依赖拒绝未授权调用。

新项目应让路由元数据和后端权限注册表复用同一组稳定 `FeatureKey`。若需要“任一权限”或“全部权限”，在元数据中显式声明模式，不要依赖菜单名称或角色名称猜测。

## 可复用的推荐设计

原始实现同时读取 `/auth/permissions` 和 `/users/permissions`，是后端 RBAC 接口切换过程中的兼容措施。新项目不应长期维护两个授权事实源；登录或恢复会话时优先请求一个原子授权快照：

```json
{
  "user": { "id": "...", "user_code": "A001", "display_name": "..." },
  "roles": [
    { "id": "...", "code": "PURCHASER", "name": "采购员" },
    { "id": "...", "code": "APPROVER", "name": "审批人" }
  ],
  "permissions": ["menu:purchase", "purchase:order:read:list"],
  "authorization_version": "2025-11-03T13:45:13Z"
}
```

前端只需把该响应规范化一次：角色转为 `Set<string>`，权限转为 `Set<string>` 或 `Record<string, true>`。`authorization_version` 可由角色、角色功能或用户角色关联的版本组成，用于明确缓存是否失效；它不是对权限内容做弱哈希的替代品。

建议生命周期：

1. 登录成功后拉取授权快照，再进入受保护页面。
2. 冷启动从本地恢复 token 仅用于恢复会话；在首次需要访问受保护路由前重新验证 token 并同步授权快照。
3. 管理员修改用户角色或角色权限后，发布失效事件、递增授权版本或要求明确刷新。多实例场景不能只依赖浏览器内存状态。
4. 刷新失败必须向上报错或使用带版本和有效期的明确旧快照，不能静默把网络/数据库故障解释为空权限。原始提交中 `catch` 后返回空映射或跳过角色同步仅用于迁移可用性，不是推荐错误策略。
5. 登出、401 和账号切换时删除 token、用户、角色、权限快照及其版本，再重置权限判断缓存。

当前项目已在原始提交之上增加请求去重、30 分钟权限同步间隔、`permissionVersion` 和 `refreshPermissions()`。这些是运行时演进，不属于 `cda2ac7b` 的原始变更；其它项目应先实现单一快照和明确失效，再按实际请求量增加缓存。

## 迁移验收清单

- 一个用户绑定两个不同角色后，`roles` 完整返回，两者的权限都能访问，且不存在覆盖或遗漏。
- 旧组件只读取 `role` 时仍能显示兼容主角色；所有新授权判断都以 `roles` 或 `permissions` 为准。
- 登录、刷新页面、手动刷新权限、登出和切换账号后，内存状态与本地缓存中的角色/权限一致。
- 路由守卫在授权快照准备完成后再做跳转；直接访问受保护 API 仍由服务端返回 401/403。
- `hasAnyRole`、`hasAllRoles`、`hasAnyPermission`、`hasAllPermissions` 的 OR/AND 语义和管理员短路有单测。
- 角色或权限变更后，缓存失效策略能让菜单、路由和按钮在约定时限内同步；失败不会被伪装为“用户无权限”。
- 侧边栏菜单过滤至少有组件测试。当前 `AppSidebar` 的 `hasMenuAccess()` 和 `hasModuleAccess()` 没有覆盖测试，迁移时应补上。

## CodeGraph 复核路径

| 层次 | 当前实现 | 追踪结论 |
| --- | --- | --- |
| 授权快照 API | `src/services/auth.ts:getUserPermissionSummary` | `GET /users/permissions` 返回角色列表和权限集合；当前类型同时兼容 PascalCase 与 snake_case 角色字段。 |
| 状态归并 | `src/stores/user.ts` | 负责登录、冷启动校验、授权快照合并、权限版本、缓存清理和判断缓存失效。 |
| 角色与权限入口 | `src/composables/usePermission.ts` | 将 `hasRole`、任一/全部角色和权限判断统一代理给 store；约 162 个调用方。 |
| 路由 UX 控制 | `src/router/permissionGuard.ts`、`src/router/index.ts` | 基于 `featureKey`、`permissions`、`anyPermissions` 过滤导航；有路由守卫测试。 |
| 导航 UX 控制 | `src/components/layout/AppSidebar.vue` | `hasMenuAccess` 和 `hasModuleAccess` 复用 store 权限判断；尚无覆盖测试。 |
| 服务端事实源 | `backend/JSECommon` 的用户权限与授权依赖 | 权限并集由有效用户角色和角色功能产生，API 端点必须独立执行授权。 |

## Git 复核

```bash
git -C frontend/JSE_UI_AI show --stat --oneline cda2ac7b
git -C frontend/JSE_UI_AI diff --ignore-space-at-eol cda2ac7b^ cda2ac7b -- src/services/auth.ts src/stores/user.ts
git -C frontend/JSE_UI_AI show cda2ac7b -- src/services/auth.ts src/stores/user.ts
```
