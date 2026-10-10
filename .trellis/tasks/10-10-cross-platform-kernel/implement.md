# implement.md — 跨端共享内核落地

## Preconditions

1. 已复核 [prd.md](prd.md) 与父任务 [design.md](../10-10-react-native-app/design.md)。
2. 本任务**必须先于** `10-10-mobile-app-slice` 完成。
3. 在编辑前加载 `.trellis/spec/frontend/` 与 `.trellis/spec/guides/` 的相关规格（见下方同步清单）。

## 执行顺序

每一步结束后都要跑最小验证，再进入下一步。

### 步骤 1：包骨架与 workspace 接线

- [ ] 建 `packages/{contract,domain,tokens}/` 与各自 `package.json`（名称 `@repo/contract` / `@repo/domain` / `@repo/tokens`）。
- [ ] 根 `package.json` 的 `workspaces` 加入 `packages/*`。
- [ ] 各包 `tsconfig.json`（`moduleResolution: "bundler"`，与 `frontend/tsconfig.json` 对齐）。
- [ ] 验证：`bun install` 通过；从 `frontend` 能解析 `@repo/domain`。

### 步骤 2：契约迁移（本任务风险最高的一步）

- [ ] `git mv frontend/src/client packages/contract/src/generated`。
- [ ] `git mv frontend/openapi-ts.config.ts packages/contract/`，`output` 改为 `./src/generated`。
- [ ] `git mv frontend/openapi.json packages/contract/`。
- [ ] 建 `packages/contract/src/index.ts`，**显式**再导出 `./generated` 及 `./generated/core/{request,ApiRequestOptions,OpenAPI,ApiError}`（生成物的 `index.ts` 默认不含 core）。
- [ ] 建 3 个再导出 shim：
  - `frontend/src/client/index.ts` → `export * from "@repo/contract"`
  - `frontend/src/client/core/request.ts` → `export { request } from "@repo/contract"`
  - `frontend/src/client/core/ApiRequestOptions.ts` → `export type { ApiRequestOptions } from "@repo/contract"`
- [ ] 建 `packages/contract/src/client-host.ts`（`ApiClientHost` + `configureApiClient`）。
- [ ] **验证**：`bun run build` 通过，且 `git diff --stat` 中**不出现**任何 `frontend/src/**` 消费者文件（38 个零改动）。
- [ ] **验证**：`git ls-files frontend/src/client` 只剩 3 个 shim 文件。

### 步骤 3：生成链路改写

- [ ] `scripts/generate-client.sh`：OpenAPI 导出目标 → `packages/contract/openapi.json`；`--filter` 目标 → `@repo/contract`；`normalize` 参数 → `packages/contract/src/generated`；`biome ci` 工作目录 → `packages/contract`。
- [ ] **验证**：`bash ./scripts/generate-client.sh && git diff --exit-code` 为空（父任务 E2E-009）。

### 步骤 4：`@repo/domain`

- [ ] `git mv frontend/src/shared/permissions/index.ts packages/domain/src/permissions/index.ts`，并在原位置留 `export * from "@repo/domain/permissions"`。
- [ ] `frontend/src/app/permissions.ts`：把 `myPermissionsQueryOptions` / `classifyPermissionQueryError` / `MyPermissions` 移到 `packages/domain/src/permissions/query.ts`；原文件改为再导出，**保留** `readMyPermissionsForRoute()`（依赖 Web 专属 `queryClient` 单例）。
- [ ] `git mv frontend/src/app/query-retry.ts packages/domain/src/http/query-retry.ts`，原位置留再导出。
- [ ] `git mv frontend/src/features/inventory/api.ts packages/domain/src/inventory/queries.ts`，原位置留再导出。**这是门禁规则 4 的验证点**：URL 与 query 参数映射从此只存在于 `packages/domain`。
- [ ] 拆 `frontend/src/app/query-client.ts`：`packages/domain/src/auth/session.ts`（`isInvalidSessionError` / `clearAuthQueries`）+ `packages/domain/src/query-client.ts`（`createQueryClient({ onAuthFailure })`）；Web 侧注入 `window.location` 与 `localStorage`。
- [ ] **验证**：`bun run build` 通过；Web 行为不变（`createQueryClient` 内部沿用原 `shouldRetryQuery` / `queryRetryDelay` / 认证失效判定）。
- [ ] **验证**：`packages/domain/package.json` 的 `dependencies` 不含 `react-dom` / `react-native` / `antd` / `tailwindcss` / `@tanstack/react-router`。

### 步骤 5：`@repo/tokens`

- [ ] 把 `frontend/src/index.css` 的 `:root` / `.dark` 令牌值抽到 `packages/tokens/src/tokens.ts`。
- [ ] 写 `packages/tokens/scripts/generate.mjs`：写 `frontend/src/index.css` 的 `/* @repo/tokens:start */ … /* @repo/tokens:end */` 托管块 + `packages/tokens/generated/rn-theme.ts`。
- [ ] 在 `frontend/src/index.css` 中把 `:root` / `.dark` 替换为托管块标记；**`@theme inline` 映射块与 `@import` 语句保持不动**（属 Tailwind 接线，非令牌值）。
- [ ] **验证**：生成的 `:root` / `.dark` 与迁移前**字节级一致**（`git diff` 只显示标记行与位置变化，值无变化）。
- [ ] 写 `packages/tokens/scripts/check.mjs`（供门禁规则 6 调用）。

### 步骤 6：门禁与矩阵

- [ ] 写 `scripts/check-cross-platform-boundaries.mjs`，实现父任务 design.md 第 3 节的 6 条规则；导出纯函数供测试调用（沿用 `scripts/check-thin-routes.mjs` 的结构）。
- [ ] 写 `scripts/check-cross-platform-boundaries.test.ts`：6 条规则**各有正例与反例**。
- [ ] 建仓库根 `cross-platform.matrix.json`，覆盖 `features/*` 与 `platform/*` 全部目录。
- [ ] 把门禁接入 `hooks/quality_hooks/`（与 `check-thin-routes.mjs` 同样的挂载方式）。
- [ ] **验证**：`bun test scripts/check-cross-platform-boundaries.test.ts` 与 `bun test scripts/check-thin-routes.test.ts` 均通过。

### 步骤 7：跨端规格

- [ ] 建 `.trellis/spec/cross-platform/index.md`、`kernel-sharing.md`、`platform-matrix.md`，写明：
  - 强制 1：新接口进 `packages/contract`；权限码 / query key / 校验 / 错误分类 / 业务规则进 `packages/domain`；设计令牌进 `packages/tokens`。
  - 强制 2：每个功能必须显式声明 `Web only` / `App only` / `both`。
  - 不强制 UI 对等。
  - 纪律：不得写 iOS 不兼容代码（D4）。
  - 纪律：不得使用 Basic Auth（`btoa` 在 RN 不可用，见 design.md 第 4.3 节）。
- [ ] 运行 spec wiki 维护（`spec_wiki.py index` / `lint`）。

### 步骤 8：规格与钩子同步

见下方清单，逐条处理。

### 步骤 9：工程入口

- [ ] 根 `package.json` 新增 `packages/*` 与后续 `mobile` 的脚本入口。
- [ ] 扩展 Biome 检查范围到 `packages/*`。
- [ ] **验证**：`bun run lint` + `python hooks/run_quality_hooks.py --json` 通过。

## 规格与钩子同步清单

实测得到 **15 个规格文件 + 2 个钩子文件 + 1 个生成脚本（`generate-client.sh` 的 5 行）+ biome 配置**提到 `src/client`（共 19 个文件）。按性质分三类处理：

### A 类：必改——表述「生成物**位置**」或「生成链路」

| 文件 | 行 | 现内容 | 处理 |
|---|---|---|---|
| `scripts/generate-client.sh` | 10 | `normalize … frontend/src/client` | 改为 `packages/contract/src/generated` |
| `frontend/openapi-ts.config.ts` | 5 | `output: "./src/client"` | 随文件迁到 `packages/contract/`，改为 `./src/generated` |
| `.trellis/spec/backend/async-task-guidelines.md` | 427 | Regenerate `frontend/src/client/**` | 路径改为 `packages/contract/src/generated/**` |
| `.trellis/spec/backend/database-guidelines.md` | 1354 | Never hand-edit `frontend/src/client/types.gen.ts` | 路径改为 `packages/contract/src/generated/types.gen.ts` |
| `.trellis/spec/backend/error-handling.md` | 55 | regenerate `frontend/src/client/**` | 同上 |
| `.trellis/spec/backend/index.md` | 114 | Do not patch `frontend/src/client/**` | 同上 |
| `.trellis/spec/backend/quality-guidelines.md` | 243 | Manual edits under `frontend/src/client/**` | 同上 |
| `.trellis/spec/backend/type-safety.md` | 95 | Do not patch `frontend/src/client/**` | 同上 |
| `.trellis/spec/frontend/directory-structure.md` | 44, 91 | 链接 `frontend/src/client/types.gen.ts` | 链接指向 `packages/contract/src/generated/types.gen.ts` |
| `.trellis/spec/frontend/pagination-contract.md` | 301 | 链接 `sdk.gen.ts` / `types.gen.ts` | 同上 |
| `.trellis/spec/frontend/quality-guidelines.md` | 111, 130 | 生成路径清单 / 复核提示 | 路径改为 `packages/contract/src/generated/**` |
| `.trellis/spec/frontend/type-safety.md` | 39 | Keep generated files out of manual edits | 路径改新位置 |
| `.trellis/spec/guides/code-reuse-thinking-guide.md` | 93, 175 | generated types from `frontend/src/client/**` | 路径改新位置 |
| `.trellis/spec/guides/cross-layer-thinking-guide.md` | 14, 72, 81, 107, 136 | 跨层表与说明 | 路径改新位置 |
| `.trellis/spec/index.md` | 18 | generated frontend client under `frontend/src/client/**` | 路径改新位置 |

### B 类：必审——表述「消费者从这里取类型」

这些句子在**再导出 shim** 下仍然成立，但真相源已变。逐条判断是否要加一句"真相源在 `packages/contract`"。

| 文件 | 行 | 现内容 |
|---|---|---|
| `.trellis/spec/frontend/excel-import-export.md` | 31 | JSON/multipart requests use `frontend/src/client/**` |
| `.trellis/spec/frontend/quality-guidelines.md` | 259 | API request/response types come from `frontend/src/client/**` |
| `.trellis/spec/frontend/type-safety.md` | 19 | Generated API contracts are consumed directly from `frontend/src/client/**` |
| `.trellis/spec/frontend/index.md` | 101 | Biome excludes generated paths such as `src/client/**` |

### C 类：保持——因再导出 shim 而仍然有效

| 文件 | 行 | 理由 |
|---|---|---|
| `frontend/biome.json` | 10 | `!**/src/client/**/*` 仍排除该目录；shim 是手写单行，排除无害 |
| `hooks/quality_hooks/frontend.py` | 17 | `"frontend/src/client"` 在生成路径允许列表；shim 仍在该路径下 |
| `hooks/tests/test_quality_hooks.py` | 51 | 测试夹具路径仍存在 |

**强制项**：`.trellis/spec/frontend/route-permission-navigation-contract.md` 的措辞必须更新——它现在说权限真相源 "remain in `shared/permissions/*`"，迁移后应改为「`shared/permissions/*` 是 `@repo/domain` 的再导出入口；真相源在 `packages/domain`」。**这是强制更新项，不是可选项。**

## Validation Commands

```bash
bun install
bun run build
bun run lint
python hooks/run_quality_hooks.py --json
bun test scripts/check-cross-platform-boundaries.test.ts
bun test scripts/check-thin-routes.test.ts
bash ./scripts/generate-client.sh && git diff --exit-code
git diff --check
```

## Review Gate

- AC-K1 ~ AC-K11 全部满足。
- 父任务 E2E-009、E2E-010 通过。
- 38 个消费者零改动（`git diff --stat` 证明）。
- 本任务通过后才可启动 `10-10-mobile-app-slice`。

## Rollback Points

| 点 | 回滚方式 |
|---|---|
| 步骤 2 后 Web 构建失败 | 恢复 `frontend/src/client` 与 `openapi-ts.config.ts` 的原位置；`packages/` 骨架保留 |
| 步骤 4 后 Web 行为变化 | 恢复 `shared/permissions` / `app/permissions.ts` / `query-retry.ts` / `inventory/api.ts` 的原实现；`packages/domain` 保留待重试 |
| 步骤 5 后 CSS 值变化 | 恢复 `index.css` 的 `:root` / `.dark` 原块（令牌值必须字节级一致，任何差异即回滚） |

**关键保证**：迁移全程 Web 侧有再导出 shim 兜底，任一阶段失败都只需回退该阶段，不影响已完成阶段。

## Validation Notes

（执行时在此记录命令输出与结论）
