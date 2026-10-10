# design.md — 跨端架构设计（Web + React Native）

本文件是 D1–D7 的技术落地设计。需求与决策依据见 `prd.md`，外部系统参考见 `research-zqsystem-cross-platform.md`。

## 1. 决策速查

| 决策 | 内容 | 一句话 |
|---|---|---|
| D1 | 共享领域内核 + 各端独立 UI | 内核一次 + UI 两次 |
| D2 | `packages/{contract,domain,tokens}` + `mobile/` | 三包 + 一工程 |
| D3 | Expo（Expo Go 起步） | 零原生工具链 |
| D4 | 只做 Android | 内部分发 |
| D5 | 强制内核共享 + 显式上端决策 | 不强制 UI 对等 |
| D6 | 首批 = 登录 + 只读 + 扫码 | 无离线、无推送 |
| D7 | 扫码 = 单据号 | 后端零改动 |

## 2. 目标仓库结构

```
repo root
├── backend/                          # 不变
├── frontend/                         # Web，不变
├── mobile/                           # 新增：Expo App
└── packages/
    ├── contract/                     # 生成物 + 平台中立请求层
    ├── domain/                       # 手写领域语义（无 UI 依赖）
    └── tokens/                       # 设计令牌单一真相源
```

### 包命名

`@repo/contract`、`@repo/domain`、`@repo/tokens`。前缀 `@repo/` 为 monorepo 惯例，避免与 npm 公开包冲突。

### 各包内部结构

```
packages/contract/
├── openapi-ts.config.ts              # 从 frontend/ 迁入
├── openapi.json                      # 从 frontend/ 迁入（生成产物）
├── src/
│   ├── generated/                    # openapi-ts 输出（原 frontend/src/client）
│   │   ├── index.ts
│   │   ├── sdk.gen.ts
│   │   ├── types.gen.ts
│   │   ├── schemas.gen.ts
│   │   └── core/                     # request.ts / OpenAPI.ts / ApiError.ts 等 5 个
│   ├── client-host.ts                # configureApiClient 接缝
│   └── index.ts                      # 公开出口
└── package.json

packages/domain/
├── src/
│   ├── permissions/
│   │   ├── index.ts                  # ← frontend/src/shared/permissions/index.ts
│   │   └── query.ts                  # ← frontend/src/app/permissions.ts 的平台中立部分
│   ├── http/
│   │   └── query-retry.ts            # ← frontend/src/app/query-retry.ts（已验证平台中立）
│   ├── auth/
│   │   └── session.ts                # isInvalidSessionError / clearAuthQueries
│   ├── query-client.ts               # createQueryClient({ onAuthFailure })
│   ├── inventory/
│   │   └── queries.ts                # ← frontend/src/features/inventory/api.ts（URL + query 映射）
│   └── index.ts
└── package.json

packages/tokens/
├── src/
│   ├── tokens.ts                     # 单一真相源（oklch 值、radius 等）
│   └── index.ts
├── scripts/
│   ├── generate.mjs                  # 写 frontend/src/index.css 托管块 + rn-theme.ts
│   └── check.mjs                     # 门禁：托管块与 tokens.ts 是否同步
├── generated/
│   └── rn-theme.ts                   # RN 主题（生成）
└── package.json
```

## 3. 依赖方向与门禁

### 允许的依赖

```
frontend ──┐                  frontend ──┐
           ├──→ domain ──→ contract      ├──→ tokens
mobile   ──┘                  mobile   ──┘
```

| 包 | 允许依赖 |
|---|---|
| `@repo/tokens` | **无运行时依赖** |
| `@repo/contract` | `axios`、`zod` |
| `@repo/domain` | `@repo/contract`、`@tanstack/react-query`、`zod` |
| `frontend` | `@repo/domain`、`@repo/tokens`（`contract` 经 domain 传递） |
| `mobile` | `@repo/domain`、`@repo/tokens`（同上） |

### 禁止的依赖

- `frontend` ↔ `mobile` **互相引用**（任一方向都不允许）
- `domain` → `react-dom` / `react-native` / `antd` / `tailwindcss` / `@tanstack/react-router`
- `contract` → 任何 UI 库或 DOM API
- `tokens` → 任何运行时依赖

### 门禁脚本

新增 `scripts/check-cross-platform-boundaries.mjs`（+ `scripts/check-cross-platform-boundaries.test.ts`，沿用 `scripts/check-thin-routes.mjs` 范式）。它检查 6 条规则：

| # | 规则 | 对应要求 |
|---|---|---|
| 1 | 各 `packages/*/package.json` 的 `dependencies` 不含被禁止的包 | D2 |
| 2 | `packages/**/*.ts` 的 import 语句不含被禁止的模块 | D2 |
| 3 | `frontend/**` 不 import `mobile/**`，反之亦然 | D2 |
| 4 | **`/api/v1/` 字符串字面量只允许出现在 `packages/domain` 与 `packages/contract`** | D5 强制 1 |
| 5 | 每个 `frontend/src/features/*` 与 `frontend/src/platform/*` 目录都在上端矩阵中有条目 | D5 强制 2 |
| 6 | `frontend/src/index.css` 的托管块与 `packages/tokens/src/tokens.ts` 一致 | R10 |

**规则 4 是消除 zqsystem N-c 失败模式的机械保证**：它把"接口 URL 与查询参数映射"物理上锁进共享层。当前 `frontend/src/features/inventory/api.ts` 正是这条规则的第一个违反者——迁移它就是 AC5 的验证点。

## 4. `@repo/contract` 设计

### 4.1 生成物迁移

| 现在 | 迁移后 |
|---|---|
| `frontend/openapi.json` | `packages/contract/openapi.json` |
| `frontend/openapi-ts.config.ts`（`output: "./src/client"`） | `packages/contract/openapi-ts.config.ts`（`output: "./src/generated"`） |
| `frontend/src/client/**`（10 文件 / 5706 行） | `packages/contract/src/generated/**` |

`scripts/generate-client.sh` 必须改为：

```bash
cd backend
uv run python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../packages/contract/openapi.json
cd ..
bun run --filter @repo/contract generate-client
bun scripts/normalize-generated-client-whitespace.mjs packages/contract/src/generated
cd packages/contract
bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true src
```

（`scripts/normalize-generated-client-whitespace.mjs` 接受目录参数，无需改逻辑，只改调用点。）

**迁移爆炸半径（已实测，比"38 个消费者"大得多）**：

| 类别 | 数量 | 内容 |
|---|---|---|
| Web 消费者 | **38 个文件** | `import ... from "@/client"` |
| 规格文件 | **15 个** | `backend/`(6) + `frontend/`(6) + `guides/`(2) + `spec/index.md`(1)；`spec/log.md` **不在其中**（它不含 `src/client`） |
| 质量钩子 | 2 处 | `hooks/quality_hooks/frontend.py:17`（生成路径允许列表）、`hooks/tests/test_quality_hooks.py:51` |
| 构建配置 | 1 处 | `frontend/biome.json:10` 的 `"!**/src/client/**/*"` |
| 生成脚本 | 1 文件 / 5 行 | `scripts/generate-client.sh` 的 7（`../frontend/openapi.json`）、9（`--filter frontend`）、10（`frontend/src/client`）、11（`cd frontend`）、12（`src`）行 |

**决定：生成物物理迁移到 `packages/contract/src/generated`，并在 `frontend/src/client/` 保留再导出 shim。**

**深路径发现（已实测）**：38 个消费者全部走 `@/client` index 路径，其中 **2 个额外**使用了 `@/client/core/*` 深路径，单靠 `frontend/src/client/index.ts` 无法覆盖这 2 个额外 import：

| 文件 | 深路径 import |
|---|---|
| `frontend/src/features/inventory/api.ts:10` | `import { request } from "@/client/core/request"` |
| `frontend/src/shared/excel/excel.ts:2` | `import type { ApiRequestOptions } from "@/client/core/ApiRequestOptions"` |

因此需要 **3 个 shim 文件**（而不是 1 个）：

```ts
// frontend/src/client/index.ts
export * from "@repo/contract"

// frontend/src/client/core/request.ts
export { request } from "@repo/contract"

// frontend/src/client/core/ApiRequestOptions.ts
export type { ApiRequestOptions } from "@repo/contract"
```

**前提**：`packages/contract/src/index.ts` 必须显式再导出这些 core 成员（生成物的 `index.ts` 默认不含 `core/request`）：

```ts
// packages/contract/src/index.ts
export * from "./generated"
export * from "./generated/core/request"
export * from "./generated/core/ApiRequestOptions"
export * from "./generated/core/OpenAPI"
export * from "./generated/core/ApiError"
export { configureApiClient } from "./client-host"
export type { ApiClientHost } from "./client-host"
```

```ts
// frontend/src/client/index.ts —— 迁移后仅此一行
export * from "@repo/contract"
```

**理由**：

1. **38 个消费者零改动** —— 全部走 `@/client` index 路径，其中 2 个额外走 `@/client/core/*` 深路径；3 个 shim 文件覆盖全部；AC6 风险大幅降低。
2. **`biome.json` 排除项与钩子允许列表仍然有效** —— `frontend/src/client/**` 依旧存在（虽然只剩 3 个再导出 shim 文件）。
3. **依赖方向正确** —— `frontend → contract`、`mobile → contract`，`frontend` 与 `mobile` 不互相引用。
4. **与 §5.4 权限再导出策略一致** —— 同一套"真相源在 `packages/`，Web 侧保留入口"的手法。

**不采用 tsconfig path 别名**（`"@/client": ["../../packages/contract/src"]`）：它能让 38 处零改动（含 2 处深路径），但会掩盖真实依赖方向，并使门禁规则 4 的边界检查失效。

**仍需修改的**：上表"规格文件"中把**生成物位置**表述从 `frontend/src/client/**` 改为 `packages/contract/src/generated/**` 的文件（清单见 `implement.md`）。表述为"消费者从这里导入类型"的句子**无需修改**——再导出使其仍然成立。

### 4.2 请求层接缝

现状（`frontend/src/main.tsx:14-18`）已经是一个接缝，只是写死在 Web 引导里：

```ts
OpenAPI.BASE = import.meta.env.VITE_API_URL
OpenAPI.TOKEN = async () => localStorage.getItem("access_token") || ""
OpenAPI.interceptors.response.use(captureRateLimitResponse)
```

`packages/contract` 把它抽成显式接口：

```ts
// packages/contract/src/client-host.ts
export interface ApiClientHost {
  baseUrl: string
  /** 平台注入：Web 用 localStorage，App 用 expo-secure-store */
  getToken: () => Promise<string | null>
  /** 平台注入：认证失效时的宿主反应（Web 跳 /login，App 跳登录页） */
  onAuthFailure?: (error: unknown) => void
}

export function configureApiClient(host: ApiClientHost): void
```

内部设置 `OpenAPI.BASE` / `OpenAPI.TOKEN`，并注册限流拦截器。

**关键点**：`OpenAPI.TOKEN` 本身就是 **async** 的，所以 `expo-secure-store` 的异步读取天然适配——这是现有生成物已经具备的能力，不需要改生成代码。

### 4.3 已知限制：`btoa`

`packages/contract/src/generated/core/request.ts:31-37`：

```ts
export const base64 = (str: string): string => {
  try { return btoa(str); }
  catch (err) { return Buffer.from(str).toString('base64'); }
};
```

RN/Hermes 中 `btoa` 与 `Buffer` 都可能不存在。该函数**只被 Basic Auth 路径调用**，而 App 只用 Bearer JWT，因此不可达。

**设计决定**：**不修改生成代码**（会被下次生成覆盖）。改为在 `mobile/` 引导里提供兜底 polyfill，并在 `.trellis/spec/cross-platform/` 中记录"不得使用 Basic Auth"。

## 5. `@repo/domain` 设计

### 5.1 首批迁入内容

| 来源 | 迁入后 | 说明 |
|---|---|---|
| `frontend/src/shared/permissions/index.ts` | `domain/src/permissions/index.ts` | `PermissionCode`（15 个码）+ `hasPermission` + `isSafeInternalPath`。**已是纯函数、无 DOM 依赖**，可原样搬。**Web 侧保留再导出**（见 5.4）。 |
| `frontend/src/app/permissions.ts` | `domain/src/permissions/query.ts` | `myPermissionsQueryOptions`（queryKey `["iam","permissions"]`、`staleTime: 30_000`）、`classifyPermissionQueryError`、`MyPermissions` 类型。**Web 侧保留再导出 + `readMyPermissionsForRoute()`**（见 5.4）。 |
| `frontend/src/app/query-retry.ts` | `domain/src/http/query-retry.ts` | **已验证平台中立**：只依赖 `axios` 与 `ApiError`。含 429 / `Retry-After` / 取消 / 状态码分类逻辑。 |
| `frontend/src/features/inventory/api.ts` | `domain/src/inventory/queries.ts` | 6 个查询函数 + URL/query 参数映射。**这是规则 4 的验证点。** |
| `frontend/src/app/query-client.ts` 的判定部分 | `domain/src/auth/session.ts` + `domain/src/query-client.ts` | 认证失效判定 + `QueryClient` 构造（`onAuthFailure` 由宿主注入）。 |

### 5.2 认证接缝

现状 `frontend/src/app/query-client.ts` 把三件事混在一起：

```ts
export const clearAuthState = () => {
  localStorage.removeItem("access_token")          // ← Web 专属
  queryClient.removeQueries({ queryKey: ["currentUser"] })      // ← 中立
  queryClient.removeQueries({ queryKey: ["iam", "permissions"] }) // ← 中立
}
// handleApiError 里还有：window.location.href = "/login"  ← Web 专属
```

拆分后：

```ts
// domain/src/auth/session.ts
export function isInvalidSessionError(error: unknown): boolean
export function clearAuthQueries(client: QueryClient): void

// domain/src/query-client.ts
export function createQueryClient(options: {
  onAuthFailure: (error: unknown) => void
}): QueryClient
```

宿主侧：

```ts
// frontend/src/app/query-client.ts（改造后）
export const queryClient = createQueryClient({
  onAuthFailure: () => { window.location.href = "/login" },
})
export const clearAuthState = () => {
  localStorage.removeItem("access_token")
  clearAuthQueries(queryClient)
}

// mobile/src/platform/query-client.ts
export const queryClient = createQueryClient({
  onAuthFailure: () => { router.replace("/login") },
})
export const clearAuthState = async () => {
  await SecureStore.deleteItemAsync("access_token")
  clearAuthQueries(queryClient)
}
```

**AC6 保证**：`createQueryClient` 内部使用与现状完全相同的 `shouldRetryQuery` / `queryRetryDelay` / 认证失效判定，Web 行为不变。

### 5.3 为什么 domain 不含 UI

`domain` 只导出**纯函数、query options、query client 工厂、类型**。它不含任何 JSX、不含 hooks 之外的 React 组件。Web 与 App 各自消费同一份 query options，各自渲染自己的 UI——这就是 D1 的"内核一次 + UI 两次"。

### 5.4 规格钉住的位置：再导出而非搬迁

`.trellis/spec/frontend/route-permission-navigation-contract.md` 把权限真相源**显式钉在两个位置**：

- `shared/permissions/*` —— "pure permission predicates and the `PermissionCode` union **remain in** `shared/permissions/*`"
- `app/permissions.ts` —— "Permission data is queried through `app/permissions.ts`"

且该 spec 的 Trigger 明确包含 "changes `shared/permissions/*`"，Validation 要求 `bun run lint` + `bun run build`。

**决定：搬迁到 `packages/domain` 后，Web 侧保留再导出（re-export shim），不删除原文件。**

| 文件 | 迁移后内容 |
|---|---|
| `frontend/src/shared/permissions/index.ts` | `export * from "@repo/domain/permissions"` —— 单行再导出 |
| `frontend/src/app/permissions.ts` | 再导出 `myPermissionsQueryOptions` / `classifyPermissionQueryError` / `MyPermissions`，并**保留** `readMyPermissionsForRoute()`（它依赖 Web 专属的 `queryClient` 单例） |

**理由**：

1. **AC6 优先**：4 个 `@/shared/permissions` 引用点与 8 个 `@/app/permissions` 引用点**无需改动**，Web 行为不可能变化。
2. **spec 仍然成立**：真相源只有一个（`packages/domain`），而 `shared/permissions` 与 `app/permissions` 仍是它的**唯一入口**——spec 的意图（权限真相集中、不得各自发明）被保留，而不是被绕过。
3. **迁移风险隔离**：P1 的 38 个 `@/client` 引用改写已经足够大，不再叠加权限路径改写。

**代价**：多一层间接，"真相源在哪"需要读文件才知道。因此 **P6 必须修改该 spec**，把措辞从 "remain in `shared/permissions/*`" 改为 "`shared/permissions/*` 是 `@repo/domain` 的再导出入口；真相源在 `packages/domain`"。**这是强制 spec 更新项，不是可选项。**

## 6. `@repo/tokens` 设计

### 6.1 现状

`frontend/src/index.css`（124 行）结构：

```css
@import "tailwindcss";
@import "tw-animate-css";
@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-primary: var(--primary);
  /* …约 30 个 --color-* 映射… */
}

:root {
  --radius: 0.625rem;
  --primary: oklch(0.5982 0.10687 182.4689);
  /* … */
}

.dark {
  --primary: oklch(0.65 0.10687 182.4689);
  /* … */
}
```

### 6.2 设计

`packages/tokens/src/tokens.ts` 成为**唯一真相源**：

```ts
export const lightTokens = {
  radius: "0.625rem",
  primary: "oklch(0.5982 0.10687 182.4689)",
  // …
} as const

export const darkTokens = {
  primary: "oklch(0.65 0.10687 182.4689)",
  // …
} as const
```

`packages/tokens/scripts/generate.mjs` 生成两处产物：

1. **`frontend/src/index.css` 的托管块** —— 夹在标记之间：
   ```css
   /* @repo/tokens:start — 由 packages/tokens 生成，请勿手改 */
   :root { … }
   .dark { … }
   /* @repo/tokens:end */
   ```
   `@theme inline` 映射块与 `@import` 语句**不由生成器管理**（它们属于 Tailwind 接线，不是令牌值）。

2. **`packages/tokens/generated/rn-theme.ts`** —— RN 主题对象，供 `mobile/` 消费。

**为什么用"托管块"而不是跨包 CSS `@import`**：`@import` 一个 workspace 包的 CSS 依赖 Vite 的包解析配置，是额外风险；托管块把令牌集中在一处、可被 `scripts/check-cross-platform-boundaries.mjs` 规则 6 校验同步，且不触碰构建链。

### 6.3 已知缺口

`AntdProvider.tsx` 里的 `colorPrimary: #0f766e` 与 `borderRadius: 8` 是**硬编码的十六进制**，与 CSS 变量里的 `oklch(0.5982 0.10687 182.4689)` 是两套值。本次**不合并**（避免扩大范围），但记入风险清单。

## 7. `mobile/` 工程结构

```
mobile/
├── app/                              # expo-router 文件路由
│   ├── _layout.tsx                   # Provider 栈：QueryClient / Auth / SafeArea
│   ├── login.tsx                     # 登录（写 SecureStore）
│   └── (app)/
│       ├── _layout.tsx               # 登录守卫（未登录跳 /login）
│       ├── index.tsx                 # 首页：按权限过滤的入口列表
│       ├── documents/
│       │   ├── index.tsx             # 单据列表（document_number 搜索 + 扫码入口）
│       │   └── [id].tsx              # 单据明细
│       ├── balances.tsx              # 库存余额只读
│       └── scan.tsx                  # 扫码（expo-camera CameraView）
├── src/
│   ├── platform/
│   │   ├── api/bootstrap.ts          # configureApiClient（SecureStore 注入）
│   │   ├── query-client.ts           # createQueryClient（router.replace 注入）
│   │   ├── auth/useAuth.ts           # RN 版登录/登出
│   │   └── polyfills/btoa.ts         # btoa 兜底（见 4.3）
│   └── shared/components/            # App 内部复用组件
├── app.json                          # Expo 配置（android package）
├── package.json
└── tsconfig.json
```

### 依赖

`expo`、`expo-router`、`expo-camera`、`expo-secure-store`、`@tanstack/react-query`、`@repo/domain`、`@repo/tokens`。

**不引入**：`expo-notifications`（推送，需 development build）、`expo-sqlite`（离线，D6 排除）、任何 Web UI 库。

### 首批页面与权限码

| 页面 | 端点 | 权限码 |
|---|---|---|
| `documents/index.tsx` | `GET /api/v1/inventory/documents?document_number=` | `inventory.documents.read` |
| `documents/[id].tsx` | `GET /api/v1/inventory/documents/{id}` | `inventory.documents.read` |
| `balances.tsx` | `GET /api/v1/inventory/balances/raw\|finished` | `inventory.balances.read` |
| `index.tsx` | `GET /iam/permissions`（经 `myPermissionsQueryOptions`） | — |

**AC4 的验证点**：`documents` 与 `balances` 是**两个不同权限码**。只给用户 `inventory.documents.read` 时，`balances` 入口应消失；直接访问 `balances` 时后端应返回 403。

## 8. 认证流（两端对比）

| 步骤 | Web | App |
|---|---|---|
| 登录 | `LoginService.loginAccessToken` | 同（同一生成 SDK） |
| 存 token | `localStorage.setItem` | `SecureStore.setItemAsync` |
| 读 token | `OpenAPI.TOKEN` → `localStorage` | `OpenAPI.TOKEN` → `SecureStore.getItemAsync` |
| 失效反应 | `window.location.href = "/login"` | `router.replace("/login")` |
| 清理 | `clearAuthState()`（localStorage + queries） | `clearAuthState()`（SecureStore + queries） |

**共享**：`configureApiClient`、`myPermissionsQueryOptions`、`classifyPermissionQueryError`、`isInvalidSessionError`、`createQueryClient`、全部请求类型。

## 9. 上端矩阵

`cross-platform.matrix.json`（仓库根，机器可校验）：

```json
{
  "features": {
    "items":     { "targets": ["web"] },
    "inventory": { "targets": ["web", "app"], "app_scope": "documents 列表/明细、balances 只读、扫码" },
    "scheduler": { "targets": ["web"] }
  },
  "platform": {
    "auth":   { "targets": ["web", "app"] },
    "docs":   { "targets": ["web"] },
    "system": { "targets": ["web"] }
  }
}
```

门禁规则 5 强制：`frontend/src/features/*` 与 `frontend/src/platform/*` 下的**每个目录**都必须有条目，`targets` 必须是 `["web"]` / `["app"]` / `["web","app"]` 之一。

这实现了 D5 强制 2：**不允许"忘了考虑移动端"**。新增功能时若不加矩阵条目，CI 失败。

## 10. 任务拆分与落地顺序

本任务为**父任务 + 2 个子任务**（D8）。父任务持有完整需求集与跨子任务验收项，不直接实现代码。

| 任务 | 内容 | 覆盖 AC | 前置 |
|---|---|---|---|
| `10-10-cross-platform-kernel` | 建 `packages/{contract,domain,tokens}`；生成物迁移（含 `frontend/src/client/index.ts` 再导出 shim）；规格/钩子/biome/生成脚本同步；门禁脚本 + 矩阵；跨端规格 | AC1、AC6、AC7、AC8 | 无 |
| `10-10-mobile-app-slice` | `mobile/` Expo 工程 + 登录（SecureStore）+ 单据列表/明细 + 库存余额只读 + 扫码 + RBAC 入口过滤 | AC2、AC3、AC4、AC9 | **子任务 1 完成** |
| `10-10-react-native-app`（父） | 集成复核 + **AC5**（共享层被两端真实引用） | AC5 | 两个子任务完成 |

### 子任务 1 的内部顺序（破坏性重构，风险最高）

| 步 | 内容 | 出口条件 |
|---|---|---|
| 1.1 | 建三个包骨架 + workspace 接线 | `bun install` 通过 |
| 1.2 | 生成物迁到 `packages/contract/src/generated`，`frontend/src/client/` 留 3 个再导出 shim | `bun run build` 通过，38 个消费者零改动（全部走 index；2 个额外走深路径） |
| 1.3 | `generate-client.sh` + `normalize-generated-client-whitespace.mjs` 调用点改写 | 重新生成后 `git diff` 为空 |
| 1.4 | `packages/domain` 迁入权限 / query-retry / inventory 映射 / query-client；Web 侧留再导出 | `bun run build` + `bun run lint` 通过 |
| 1.5 | `packages/tokens` + 托管块生成器；`index.css` 改为托管块 | 生成的 CSS 与迁移前**字节级一致** |
| 1.6 | 门禁脚本 + 测试 + `cross-platform.matrix.json` | `bun test scripts/check-cross-platform-boundaries.test.ts` 通过 |
| 1.7 | 规格更新（~10–12 处生成物位置表述）+ 钩子/biome 复核 + 跨端规格 | `python hooks/run_quality_hooks.py --json` 通过 |

**1.5 的出口条件很关键**：托管块生成的 CSS 必须与现有 `index.css` 的 `:root` / `.dark` **字节级一致**，否则 Web 主题会静默变化，AC6 名义通过而实际回归。

### 子任务 2 的内部顺序

| 步 | 内容 | 出口条件 |
|---|---|---|
| 2.1 | `mobile/` Expo 工程 + Metro workspace 接线 | Expo Go 能打开空壳 |
| 2.2 | `configureApiClient` + `createQueryClient` 接入 + SecureStore | 真机登录成功，token 落 SecureStore |
| 2.3 | 单据列表/明细 + 余额只读 + RBAC 入口过滤 | 只给 `inventory.documents.read` 时余额入口消失 |
| 2.4 | 扫码 → 单据号 → 列表/明细 + 未命中提示 | 真机扫到单据号能返回真实数据 |

**风险集中在子任务 1**（唯一的破坏性重构）；子任务 2 全部是新增代码，与子任务 1 零重叠。

## 11. 风险与未验证点

| # | 风险 | 缓解 |
|---|---|---|
| 1 | P1 触及 **38 个 `@/client` 消费者 + 15 个规格文件 + 2 处钩子 + biome 配置 + 1 个生成脚本（5 行）** | 再导出 shim（index + 2 个深路径）让 38 个消费者零改动；规格与钩子更新拆为独立步骤；每步跑 `bun run build` + `bun run lint` + `python hooks/run_quality_hooks.py --json` |
| 1b | `hooks/quality_hooks/frontend.py:17` 的生成路径允许列表指向 `frontend/src/client` | 因保留再导出，该路径仍存在；迁移后仍须复核 `hooks/tests/test_quality_hooks.py` |
| 2 | Metro 解析 bun workspace 的 `packages/*` | Expo 自动检测 monorepo；若 `packages/*` 未进 `watchFolders`，在 `mobile/metro.config.js` 显式添加 |
| 3 | `btoa` 在 RN 不可用 | 仅 Basic Auth 路径触达；App 引导加 polyfill |
| 4 | `expo-camera` 扫码需真机（模拟器不可用） | AC9 明确要求真机验证 |
| 5 | iOS 完全未验证（D4） | 纪律：不写 iOS 不兼容代码；风险后置 |
| 6 | 令牌与 antd 主题是两套值（`#0f766e` vs `oklch`） | 本次不合并，记入后续任务 |
| 7 | 后端 balances 不支持 `item_code` | D7 已规避（扫码选单据号） |
| 8 | `packages/*` 未纳入 Biome 检查范围 | P1 中扩展 Biome 配置 |
| 9 | 根 `package.json` 脚本全是 `--filter frontend` | P1 中新增 `mobile` / `packages` 入口 |

## 12. AC 与设计元素映射

| AC | 由什么满足 |
|---|---|
| AC1 | 第 3 节门禁脚本（6 条规则）+ 本文档 |
| AC2 | 第 8 节认证流（`expo-secure-store`）+ 第 7 节 `mobile/` |
| AC3 | 第 7 节首批页面 + 第 5.1 节 `domain/src/inventory/queries.ts` |
| AC4 | 第 7 节两个不同权限码的页面 + `domain/src/permissions/query.ts` |
| AC5 | 第 5.1 节首批迁入 + 门禁规则 4（URL 字面量锁进共享层） |
| AC6 | 第 10 节 P1 的验证要求 |
| AC7 | 第 10 节 P6 |
| AC8 | 第 10 节 P6 |
| AC9 | 第 7 节 `scan.tsx` + D7 + R11 |
