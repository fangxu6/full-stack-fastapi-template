# Spectral 使用教程（本项目）

本教程说明如何在当前仓库使用 Spectral 校验 OpenAPI 命名与错误响应规范。

- 规则文件：`docs/rules/openapi.spectral.yaml`
- 规范文档：`docs/rules/API命名规范.md`
- OpenAPI 文件：`frontend/openapi.json`

## 1. 前置条件

1. 在仓库根目录执行命令：`D:\Workspace\full-stack-fastapi-template`
2. 本机可用 `npx`（有 Node.js/npm）
3. `frontend/openapi.json` 已生成

## 2. 快速上手（推荐流程）

### Step 1：生成最新 OpenAPI

```bash
bash ./scripts/generate-client.sh
```

说明：脚本会从后端导出 OpenAPI 到 `frontend/openapi.json`，并生成前端 client。

### Step 2：执行 Spectral

```bash
npx @stoplight/spectral-cli lint frontend/openapi.json -r docs/rules/openapi.spectral.yaml
```

### Step 3：在 CI/本地只对 error 级别失败

```bash
npx @stoplight/spectral-cli lint frontend/openapi.json -r docs/rules/openapi.spectral.yaml --fail-severity error
```

## 3. 输出解读

- `error`：必须修复，代表契约或命名规范不符合要求
- `warn`：建议修复，通常是增强项或兼容期提醒

常见规则：

- `fs-path-segment-kebab-case`
  - 路径固定段应为 `kebab-case`
- `fs-parameter-name-snake-case`
  - path/query/header 参数名应为 `snake_case`
- `fs-operation-id-format`
  - `operationId` 应满足 `<tag>-<route_name>`
- `fs-422-response-ref`
  - `422` 应引用 `#/components/schemas/HTTPValidationError`

## 4. 日常开发建议

1. 修改后端 route/schema
2. 重新生成 OpenAPI（`bash ./scripts/generate-client.sh`）
3. 执行 Spectral lint
4. 修复问题后再提交代码

## 5. 常见问题

### 5.1 首次运行慢

`npx` 首次会下载 `@stoplight/spectral-cli`，属于正常行为。

### 5.2 找不到 `frontend/openapi.json`

先运行：

```bash
bash ./scripts/generate-client.sh
```

### 5.3 想把 warn 也当失败

改成：

```bash
npx @stoplight/spectral-cli lint frontend/openapi.json -r docs/rules/openapi.spectral.yaml --fail-severity warn
```

## 6. CI 示例（GitHub Actions）

```yaml
- name: Lint OpenAPI with Spectral
  run: npx @stoplight/spectral-cli lint frontend/openapi.json -r docs/rules/openapi.spectral.yaml --fail-severity error
```

## 7. 规则维护建议

- 新增/调整 API 命名策略时，先更新：
  - `docs/rules/API命名规范.md`
  - `docs/rules/openapi.spectral.yaml`
- 再执行一次 Spectral，确认规则可执行且不过度误报。
