# API 命名规范（OpenAPI 落地版）

> 相关教程：[Spectral 使用教程（本项目）](./Spectral使用教程.md)


## 1. 目的与适用范围

本文用于统一当前仓库 REST API 的命名方式，并作为 `openapi.yaml`（或等价 OpenAPI 文档）落地时的直接约束。

- 适用范围：
  - 后端 API 路径、参数、请求体、响应体命名
  - OpenAPI `paths`、`components.schemas`、`operationId`、错误响应定义
- 关联目录：
  - `backend/app/api/**`
  - `backend/app/schemas/**`
  - `frontend/openapi.json`（由后端 OpenAPI 生成）
  - `frontend/src/client/**`（生成客户端）

## 2. 命名总览

| 场景 | 规范 |
| --- | --- |
| URL path 固定段 | `kebab-case`，小写单词用 `-` 连接 |
| Path / Query / Header 参数名 | `snake_case` |
| JSON request/response 字段名 | `snake_case` |
| OpenAPI 业务 schema 名 | `PascalCase`（如 `UserCreate`、`ItemsPublic`） |
| OpenAPI 自动生成 body schema 名 | 允许 `Body_<tag>-<route_name>`（FastAPI 默认行为） |
| `operationId` | `<tag>-<route_name>`，其中 `tag` 小写，`route_name` 为 `snake_case` |
| 常量值（若在代码中出现） | `UPPER_SNAKE_CASE` |

## 3. URL 规范

### 3.1 路径命名

- 路径固定段使用小写 `kebab-case`，例如：
  - `/api/v1/login/access-token`
  - `/api/v1/password-recovery/{email}`
  - `/api/v1/utils/health-check/`
- 路径参数使用 `snake_case`，例如 `{user_id}`、`{slug}`。
- 资源命名优先名词，不使用动作式 URL（例如 `createUser`）。

### 3.2 尾斜杠策略

- 当前仓库已有尾斜杠与非尾斜杠并存（例如 `/users/` 与 `/users/me`）。
- 为避免破坏兼容性，现阶段不强制一次性统一。
- 新增路径建议在同一资源组内保持一致。

## 4. 参数与报文体字段规范

### 4.1 参数命名

- `path`、`query`、`header` 参数统一 `snake_case`。
- 分页参数沿用现有 `skip`、`limit` 语义，避免在同一 API 混用另一套分页命名。

### 4.2 JSON 字段命名

- 请求体与响应体字段统一 `snake_case`。
- 推荐语义：
  - 布尔字段：`is_*` / `has_*`
  - 时间字段：`*_at`
  - 关联字段：`*_id`
- 禁止同一接口同时混用 `camelCase` 与 `snake_case` 字段名。

## 5. OpenAPI 对象命名规范

### 5.1 `components.schemas`

- 业务 schema 使用 `PascalCase`，例如 `UserPublic`、`RuleDocumentPublic`。
- FastAPI 对 `application/x-www-form-urlencoded` 等场景自动生成的 schema 命名可保留：
  - `Body_<tag>-<route_name>`

### 5.2 `operationId`

- 按当前后端实现，`operationId` 采用：
  - `<tag>-<route_name>`
- 约束：
  - `tag`：小写字母开头，仅含小写字母与数字
  - `route_name`：`snake_case`

## 6. 错误响应结构（按当前代码基线）

### 6.1 业务错误（HTTPException）

当前服务层和依赖层广泛使用 `HTTPException(status_code=..., detail=...)`。
因此业务错误响应应保持 FastAPI 默认结构：

```json
{
  "detail": "Not enough permissions"
}
```

约束：

- 不额外包装 `code/message/data` 外层壳。
- `detail` 语义清晰、面向调用方可读。

### 6.2 参数校验错误（422）

沿用 FastAPI 默认 `HTTPValidationError`：

```json
{
  "detail": [
    {
      "loc": ["body", "new_password"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

其中：

- `detail` 为数组
- 每项至少包含：`loc`、`msg`、`type`

### 6.3 与前端约定

前端错误提取逻辑当前已兼容两类结构：

- `detail: string`（业务错误）
- `detail: ValidationError[]`（422 校验错误）

新增接口应保持兼容该模式，避免引入新的错误包装层。

## 7. OpenAPI 落地清单

在维护 `openapi.yaml`（或检查生成结果）时，至少确认：

1. 路径固定段是否为 `kebab-case`。
2. 参数名与 JSON 字段是否全部为 `snake_case`。
3. `operationId` 是否符合 `<tag>-<route_name>`。
4. 业务 schema 是否使用 `PascalCase`。
5. `422` 是否引用 `#/components/schemas/HTTPValidationError`。
6. 若定义了 4xx/5xx JSON 错误响应，是否包含可解析的 `detail` 字段语义。

## 8. Spectral 校验

配套规则文件：`docs/rules/openapi.spectral.yaml`。

示例命令：

```bash
npx @stoplight/spectral-cli lint frontend/openapi.json -r docs/rules/openapi.spectral.yaml
```

若后续改为维护独立 `openapi.yaml`，将命令中的目标文件替换为实际路径即可。

