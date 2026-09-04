# 权限完成

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)  
> 复用定位：将 JWT 认证、数据库用户、角色聚合和细粒度 API 授权收敛为一条可复用的 FastAPI 后端链路。

## 提交信息

- 仓库：`JSECommon`
- SHA：`b6e8fbbb`
- 日期：`2025-10-31`
- 父提交：`c87d91db`
- 作者：`hanqiang <240448317@qq.com>`
- 分类：后端：权限、运行时与基础能力
- 原始主题：权限完成

## 这次提交解决的问题

此前系统同时存在旧 `Role` 模型、配置里的固定管理员角色和新的 `Common_*` RBAC 表，部分路由甚至处于“只认证、不授权”或临时放行状态。`b6e8fbbb` 完成了切换：

- 删除旧 `app/api/v1/routes/roles.py`、`app/crud/role.py`、`app/models/role.py`，以 `Common_Role_Master`、`Common_Role_FeatureDetail` 和 `Common_User_RoleDetail` 为唯一授权数据源。
- `get_current_user` 从 JWT 的 `sub` 解析用户账号后回查 `Common_User`，拒绝不存在或已软删除用户，并挂载角色编码、角色名、`is_admin` 和 `UserID`。
- `require_permission`、`require_permissions`、`require_any_permission` 真正执行权限判断；管理员角色短路放行，普通用户从角色聚合有效 `FeatureKey`。
- 用户、员工、角色等管理接口改用动作级权限键，例如 `user:write:generate-account`、`employee:write:update`、`role:delete:remove`。
- 权限服务对用户权限、菜单树、按钮权限、角色分配提供统一业务入口，并在进程内增加短期缓存。
- Pydantic 请求/响应模型同时接受 Python 风格字段和数据库/前端使用的 PascalCase 字段，降低跨层命名摩擦。

这不是新增一组装饰器，而是一次“认证事实源 + 授权事实源 + 路由契约”的整体迁移。其它项目复用时应按同样顺序迁移，避免只复制 `require_permission` 却继续查询旧角色表。

## 当前端到端链路

```text
Authorization: Bearer <JWT>
            │
            ▼
get_current_user()
  1. decode_access_token(token)
  2. payload.sub -> Common_User.UserCode
  3. 查询未软删除用户
  4. 查询有效 UserRole -> Role
  5. 返回 CurrentUser（UserID、roles、role_details、is_admin）
            │
            ▼
require_permission("employee:write:update")
  1. admin 直接通过
  2. PermissionService 查询 User -> Role -> Feature
  3. 过滤 IsDeleted=0，且 only_enabled 时过滤角色/功能 IsEnabled=1
  4. 权限键匹配成功则进入路由，否则 HTTP 403
            │
            ▼
业务路由 -> Service -> CRUD -> 数据库
```

认证和授权都在服务端完成。前端菜单、按钮和路由可以隐藏入口，但不能替代这条链路。

## 可迁移数据模型

| 实体 | 关键字段 | 运行时作用 |
| --- | --- | --- |
| `Common_User` | `UserID`、`UserCode`、`IsEnabled`、`IsDeleted` | JWT 的账号映射和登录主体；密码字段只在认证内部使用。 |
| `Common_Role_Master` | `RoleID`、`RoleCode`、`IsEnabled`、`IsSystem`、`IsDeleted` | 角色定义；`RoleCode=ADMIN` 是当前超级管理员判定约定。 |
| `Common_Feature` | `FeatureID`、`FeatureKey`、`FeatureType`、`ParentID`、状态字段 | 授权原子和菜单树节点。 |
| `Common_User_RoleDetail` | `UserID`、`RoleID`、`IsDeleted` | 用户与角色的多对多关系。 |
| `Common_Role_FeatureDetail` | `RoleID`、`FeatureID`、`IsDeleted` | 角色与功能的多对多关系。 |

当前使用 MySQL `BINARY(16)` UUID；API 和日志边界会将 UUID 转换为字符串。迁移到其它数据库时可改用原生 UUID，但关联查询、序列化和审计字段必须统一类型。

### 有效权限的定义

当 `only_enabled=True` 时，只有同时满足以下条件的关联才产生权限：

```text
UserRole.IsDeleted = 0
RoleFeature.IsDeleted = 0
Role.IsDeleted = 0 AND Role.IsEnabled = 1
Feature.IsDeleted = 0 AND Feature.IsEnabled = 1
```

最终结果是去重后的 `Feature.FeatureKey` 集合。多角色权限采用并集，不存在显式 deny 规则；如果目标项目需要拒绝优先级或数据范围，应扩展策略模型，不要用删除关联来模拟 deny。

## 授权依赖契约

实现位于 `app/core/dependencies.py`，`app/dependencies/current_user.py` 只是兼容性重导出层。

```python
@router.put("/employees/{employee_id}")
async def update_employee(
    data: EmployeeUpdate,
    current_user=Depends(require_permission("employee:write:update")),
):
    ...

@router.get("/reports")
async def read_report(
    current_user=Depends(require_permissions("report:read", "report:export")),
):
    ...

@router.get("/shared")
async def shared(
    current_user=Depends(require_any_permission("team:read", "team:members:manage")),
):
    ...
```

- `require_permission(key)`：单键检查。
- `require_permissions(*keys)`：所有键都满足（AND）。空参数不增加限制。
- `require_any_permission(*keys)`：任一键满足（OR）。空参数不增加限制。
- `require_role(*roles)`：按角色编码匹配，大小写不敏感。
- `require_admin()`：仅管理员角色通过。
- 未认证或 JWT 无效返回 401；用户不存在、权限不足或未绑定系统账号返回 403。

### 权限键命名

本提交开始将粗粒度键拆为动作级键：

| 操作 | 示例 |
| --- | --- |
| 列表/查看 | `employee:read`、`employee:read:export` |
| 创建 | `employee:write:create` |
| 更新 | `employee:write:update` |
| 删除 | `employee:delete:remove` |
| 特殊动作 | `employee:write:depart`、`employee:write:import` |

当前匹配函数允许前缀关系（例如已拥有 `employee:read` 可匹配更深层键），这是历史兼容策略。新项目应先决定是否需要层级继承，并将规则写成独立、可测试的策略；高风险动作建议使用精确键。

## 权限服务与缓存

`app/services/permission_service.py` 是授权查询的唯一业务入口，主要操作包括：

| 方法 | 输出 | 用途 |
| --- | --- | --- |
| `get_user_permissions` | `set[str]` | 端点鉴权、批量权限加载。 |
| `check_user_permission` / `check_user_permissions_batch` | 布尔值/映射 | 权限检查 API。 |
| `get_user_features` | 功能详情列表 | 管理端和前端功能范围。 |
| `get_user_menu_tree` | module/menu 树 | 导航生成。 |
| `get_user_button_permissions` | `parent_id -> FeatureKey[]` | 页面按钮控制。 |
| `get_user_roles` / `assign_user_roles` | 角色详情/分配结果 | 用户角色管理。 |

当前服务有进程内 TTL 缓存（默认 300 秒），键为 `(user_id, only_enabled)`；`get_current_user` 返回的对象也带 `_permission_cache`，使同一个请求内的多个依赖不会重复查库。

复用时注意：

- 多进程或多实例部署中，进程内缓存不是共享缓存；角色变更后可能在 TTL 内继续使用旧权限。需要即时生效时，使用 Redis/版本号或显式失效接口。
- 缓存只缓存“权限集合”，不缓存管理员判定和数据范围；管理员角色撤销时必须确保身份缓存也及时失效。
- 查询失败应抛出可观测异常，不能把数据库故障伪装成空权限或成功。

## 路由迁移范围

`b6e8fbbb` 调整了以下路由组：

| 路由组 | 迁移重点 |
| --- | --- |
| `auth.py` | 登录和 `/me` 返回真实角色列表；旧 `/auth/permissions` 改为从新 RBAC 聚合，保留兼容接口。 |
| `admin_users.py` | 创建、更新、删除用户使用动作级权限；创建/更新用户时同步角色关联。 |
| `employees.py` | 创建、更新、删除、离职、导入、导出分别使用细粒度权限。 |
| `rbac_roles.py` | 角色 CRUD、启停和权限分配挂上 `require_permission`；响应补充创建人/更新人账号。 |
| `features.py` | 统一 `/api/features` 路由前缀和功能树接口。 |
| `departments.py`、`logs.py`、部分查询接口 | 本提交保留“仅认证”而非细粒度授权的历史兼容行为。迁移到新项目时应逐条复核，不能据此推断所有 GET 都无需权限。 |

建议的迁移顺序：先切换 `get_current_user`，再保护写接口，最后为读接口补齐权限键并删除旧路由；每一步都用真实用户、禁用用户、无角色用户和管理员用户验证。

## 认证响应与跨层命名

`auth.py` 新增安全用户构造逻辑 `_build_safe_user`，返回角色编码和角色名称，但不返回密码字段：

```json
{
  "UserCode": "A001",
  "role": "ADMIN",
  "roles": ["ADMIN"],
  "role_names": ["系统管理员"],
  "is_active": 1
}
```

功能和角色 Schema 使用 Pydantic alias 同时兼容 `role_code`/`RoleCode`、`feature_key`/`FeatureKey` 等命名。复用时建议在 API 边界固定一种外部命名；兼容别名只作为迁移窗口，避免前端、数据库和 Python 内部长期各自维护一套字段名。

## 配置和数据库边界

本提交还做了三项基础设施调整：

- `app/core/database.py` 统一异步引擎、连接池和 `get_db` 会话依赖，异常自动 rollback，正常请求结束 commit。
- `app/core/config.py` 增加 Redis 配置（默认关闭）以及旧配置字段属性，支持后续缓存接入。
- `config/config_Feature.json`、`config/config_HeaderTrans.json` 与生成脚本继续作为配置驱动的功能/表头清单；`generate_feature_config.py` 会校验权限键唯一性和关键模块完整性。

生产复用建议：

1. 用 Alembic/SQL migration 创建 RBAC 表、索引和外键，不让应用启动隐式创建生产表。
2. 把功能配置校验作为 CI 步骤，至少检查 `FeatureKey` 唯一、父节点存在、类型合法和引用的路由权限键已注册。
3. Redis 缓存必须显式启用，并为角色/功能变更提供失效策略；默认关闭时不能假设缓存存在。
4. `get_db` 的请求级 commit 约定要与 service 层事务边界一致；若 service 自己 commit，需明确嵌套事务和失败回滚行为。

## 当前实现的复用边界

- `app/api/v1/routes/auth.py` 仍保留旧 `/permissions` 兼容端点，并在异常时返回空权限；这只能作为迁移兼容，不能作为新项目的错误处理标准。
- `app/core/dependencies.py` 中 `get_current_identity_no_db` 只验证 JWT，不回查用户和角色，适用于不需要数据库的身份日志接口，不能用于授权端点。
- 当前管理员判断基于角色编码 `ADMIN`。如果目标项目有租户、组织或多个管理员等级，应把管理员策略参数化并记录审计。
- 路由权限键和功能树 `FeatureKey` 必须来自同一注册表。只在路由常量中声明而不进入功能配置，会导致前端无法展示或角色无法分配。
- 删除旧角色表属于数据迁移动作。复制代码时必须先完成数据回填、双读校验和回滚方案，不能只删除 ORM 文件。

## CodeGraph 复核路径

| 层次 | 当前实现 | 追踪结论 |
| --- | --- | --- |
| 认证入口 | `app/core/dependencies.py:get_current_user` | JWT `sub` -> `common_user_crud.get_by_user_code` -> `crud_user_role_detail.get_user_roles` -> `CurrentUser`。 |
| 授权入口 | `app/core/dependencies.py:require_permission` | 管理员短路；普通用户调用 `_get_cached_permissions`，最终进入 `permission_service.get_user_permissions`。 |
| 权限聚合 | `app/services/permission_service.py` | UserRole、RoleFeature、Role、Feature 四表连接，过滤删除/禁用状态并去重 `FeatureKey`。 |
| 路由接入 | `app/api/v1/routes/{admin_users,employees,rbac_roles,features}.py` | 写操作已细化到 create/update/remove/import/export 等动作。 |
| 用户响应 | `app/api/v1/routes/auth.py`、`app/api/v1/routes/user_permissions.py` | 登录、`/me`、权限查询分别提供角色、权限集合、菜单树和按钮权限。 |
| 配置校验 | `scripts/generate_feature_config.py` | 在加载配置前校验权限键重复和关键业务权限缺失。 |
| 前端消费 | `frontend/JSE_UI_AI/src/stores/user.ts`、`src/services/rbac.service.ts` | 使用同一权限键控制路由、菜单、按钮和角色授权树；前端判断不构成安全边界。 |

## 迁移验收清单

- 无 token、无效 token、已删除用户分别得到 401，禁用用户不能通过 active-user 依赖访问受保护业务。
- 普通用户无权限时，直接调用受保护 API 得到 403；仅隐藏按钮不能视为通过。
- 多角色用户得到权限并集；禁用/软删除角色、功能和关联不会产生权限。
- 角色 CRUD、用户角色分配和功能树读取均使用同一 `FeatureKey` 注册表。
- 权限缓存 TTL、失效和多实例一致性策略已明确，并有角色变更后的验证用例。
- 登录和 `/me` 响应不泄露密码字段，角色编码/名称与前端类型契约一致。
- 旧 `Role` 数据已完成迁移，删除旧表前通过双读或对账确认权限集合一致。

## Git 复核

```bash
git -C backend/JSECommon show --stat --oneline b6e8fbbb
git -C backend/JSECommon show b6e8fbbb -- app/core/dependencies.py app/services/permission_service.py app/api/v1/routes/auth.py
git -C backend/JSECommon diff b6e8fbbb^ b6e8fbbb -- app/models/role.py app/models/common_role_master.py app/api/v1/routes/rbac_roles.py
```
