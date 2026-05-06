# Interface Spec

## Overview
- Auth method: 继续使用现有 Bearer token 登录态，但授权模型从单一 `is_superuser` 升级为 RBAC 权限点模型。
- Idempotency rules: 结构治理文档本身无运行时幂等要求；落地后的系统管理、角色配置、文件查询、日志查询等接口应按 REST 常规语义设计。
- Error response format: 后续新增模块统一收敛到平台级异常结构，并在批次 0 建立统一错误返回约定。

## Endpoint
- 本规范不是单一业务接口，而是一组平台能力接口约定。首批应至少包括以下接口分组：

- `GET /api/v1/iam/me/permissions`
- 返回当前用户权限集合，为前端路由守卫、菜单过滤、按钮权限控制提供基础数据。

- `GET /api/v1/iam/roles`
- `POST /api/v1/iam/roles`
- `PATCH /api/v1/iam/roles/{role_id}`
- `POST /api/v1/iam/roles/{role_id}/permissions`
- 提供角色管理与角色权限分配能力。

- `GET /api/v1/system/users`
- `GET /api/v1/system/roles`
- `GET /api/v1/system/departments`
- `GET /api/v1/system/dictionaries`
- `GET /api/v1/system/params`
- 提供系统管理模块的统一命名空间。

- `GET /api/v1/audit/logs`
- 提供统一审计日志查询入口。

- `POST /api/v1/files/upload`
- `GET /api/v1/files`
- `GET /api/v1/files/{file_id}`
- `DELETE /api/v1/files/{file_id}`
- 提供统一文件中心接口。

## Request
- `GET /api/v1/iam/me/permissions`
  - 无请求体。
  - 依赖登录态。

- `POST /api/v1/iam/roles`
  - `name: string`
  - 必填。
  - 角色名称在有效范围内唯一。
  - `code: string`
  - 必填。
  - 建议作为稳定权限标识。
  - `description: string | null`
  - 可选。

- `POST /api/v1/iam/roles/{role_id}/permissions`
  - `permission_ids: string[]`
  - 必填。
  - 角色绑定的权限点集合。

- `GET /api/v1/system/dictionaries`
  - 支持分页、类型过滤、关键词过滤。

- `POST /api/v1/files/upload`
  - `file: binary`
  - 必填。
  - `business_type: string`
  - 可选但推荐，用于建立业务归属。
  - `business_id: string`
  - 可选但推荐，与 `business_type` 配套。

- `GET /api/v1/audit/logs`
  - 支持用户、动作、对象、时间范围等筛选条件。

## Response
- `GET /api/v1/iam/me/permissions`
  - `user_id: string`
  - `roles: RoleSummary[]`
  - `permissions: string[]`
  - `menus: string[]`

- `RoleSummary`
  - `id: string`
  - `name: string`
  - `code: string`

- `GET /api/v1/system/users`
  - 延续当前分页结构：`data[] + count`
  - 用户对象应逐步扩展 `roles`、`department_id` 等平台字段。

- `GET /api/v1/system/dictionaries`
  - `data: DictTypePublic[]`
  - `count: number`

- `GET /api/v1/audit/logs`
  - `data: AuditLogPublic[]`
  - `count: number`

- `POST /api/v1/files/upload`
  - `id: string`
  - `file_name: string`
  - `content_type: string`
  - `size: number`
  - `business_type: string | null`
  - `business_id: string | null`
  - `url: string | null`

## Error Codes
- `401`: 未登录或 token 无效。
- `403`: 已登录但缺少目标权限点。
- `404`: 目标角色、文件、日志对象或系统配置项不存在。
- `409`: 角色编码、字典编码、参数编码等唯一约束冲突。
- `422`: 请求字段校验失败。
- `500`: 统一异常兜底，需附带可追踪 `request_id` / `trace_id`。

## Examples
- Success example: `GET /api/v1/iam/me/permissions`
```json
{
  "user_id": "3ab3b123-4e56-7890-abcd-111111111111",
  "roles": [
    {
      "id": "role-admin",
      "name": "Platform Admin",
      "code": "platform_admin"
    }
  ],
  "permissions": [
    "system.users.read",
    "system.users.write",
    "audit.logs.read"
  ],
  "menus": [
    "dashboard",
    "system.users",
    "audit.logs"
  ]
}
```

- Success example: `POST /api/v1/files/upload`
```json
{
  "id": "file-001",
  "file_name": "contract.pdf",
  "content_type": "application/pdf",
  "size": 24576,
  "business_type": "contract",
  "business_id": "contract-1001",
  "url": "/api/v1/files/file-001"
}
```

- Failure example:
```json
{
  "detail": "Permission denied",
  "request_id": "req-20260506-001"
}
```

## Notes
- 接口命名空间应从一开始按平台域划分，而不是继续把所有新接口放进全局 `users/items/docs` 风格平铺目录。
- 前端路由命名与菜单 key 应稳定对应权限 key，例如 `system.users.read` 对应 `/system/users` 页面的读权限。
- 前端页面必须通过 generated client 调用这些接口，不新增独立的手写请求层。
- 当前 `users/items/docs` 允许过渡期继续存在，但新增平台模块应优先走 `modules/*` 与 `platform/*` 新结构。
