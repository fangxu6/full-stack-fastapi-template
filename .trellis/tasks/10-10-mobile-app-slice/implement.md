# implement.md — React Native App 落地

## Preconditions

1. **`10-10-cross-platform-kernel` 已完成并通过其 Review Gate**——本任务依赖它交付的 `@repo/contract` / `@repo/domain` / `@repo/tokens`。未完成时不得启动本任务。
2. 已复核 [prd.md](prd.md)、父任务 [design.md](../10-10-react-native-app/design.md) 第 7–8 节、本任务 [e2e-api-tests.md](e2e-api-tests.md) 与父任务 [e2e-api-tests.md](../10-10-react-native-app/e2e-api-tests.md)。
3. **不安装 Android SDK**（本机无，也不需要）——用 Expo Go 真机验证。
4. 准备：一台 Android 手机 + Expo Go App + 与开发机同一局域网。

## 执行顺序

### 步骤 1：Expo 工程骨架

- [ ] 创建 `mobile/`（Expo + expo-router + TypeScript 模板）。
- [ ] 根 `package.json` 的 `workspaces` 加入 `mobile`；新增 `--filter mobile` 脚本入口。
- [ ] `mobile/app.json`：设 `android.package`；**不设** iOS bundle identifier（D4：本迭代不做 iOS 构建）。
- [ ] 若 Metro 解析不到 `packages/*`，在 `mobile/metro.config.js` 显式加 `watchFolders` / `nodeModulesPaths`（父任务 design.md 风险 2）。
- [ ] **验证**：`bun run --filter mobile start` 输出二维码；真机 Expo Go 能打开默认页面。

### 步骤 2：平台注入层

- [ ] `mobile/src/platform/api/bootstrap.ts`：
  ```ts
  configureApiClient({
    baseUrl: process.env.EXPO_PUBLIC_API_URL!,
    getToken: () => SecureStore.getItemAsync("access_token"),
    onAuthFailure: () => router.replace("/login"),
  })
  ```
- [ ] `mobile/src/platform/query-client.ts`：`createQueryClient({ onAuthFailure: () => router.replace("/login") })`；`clearAuthState` 用 `SecureStore.deleteItemAsync`。
- [ ] `mobile/src/platform/polyfills/btoa.ts`：兜底 `btoa`（父任务 design.md 第 4.3 节）。**不得使用 Basic Auth。**
- [ ] `mobile/src/platform/auth/useAuth.ts`：登录（`LoginService.loginAccessToken`）→ 写 SecureStore；登出 → 清 SecureStore + `clearAuthQueries`。
- [ ] **验证**：登录成功后 SecureStore 中有 token；**杀进程重启仍能读到**（真实持久化，而非内存态）。

### 步骤 3：路由与登录守卫

- [ ] `mobile/app/_layout.tsx`：`QueryClientProvider` + SafeArea + Stack。
- [ ] `mobile/app/login.tsx`：登录表单。
- [ ] `mobile/app/(app)/_layout.tsx`：未登录跳 `/login`。
- [ ] **验证**：未登录访问 `(app)` 下任一页面被重定向到登录页。

### 步骤 4：首页 + 权限过滤（AC-M3 前半）

- [ ] `mobile/app/(app)/index.tsx`：`useQuery(myPermissionsQueryOptions())`，用 `hasPermission()` 过滤入口。
- [ ] 无 `inventory.documents.read` → 不显示单据入口；无 `inventory.balances.read` → 不显示余额入口。
- [ ] **验证**：用 e2e 前置的用户 B（只有 documents 权限）与用户 C（无 documents 权限）登录，确认入口按预期隐藏。

### 步骤 5：单据列表与明细（AC-M2）

- [ ] `mobile/app/(app)/documents/index.tsx`：调 `@repo/domain` 的 inventory 查询函数（`document_number` 参数）。
- [ ] `mobile/app/(app)/documents/[id].tsx`：明细。
- [ ] **验证**：`mobile/` 中**不存在** `/api/v1/` 字符串字面量（门禁规则 4，即 AC-M5）。

### 步骤 6：库存余额只读（AC-M2）

- [ ] `mobile/app/(app)/balances.tsx`：调 `@repo/domain` 的 balances 查询函数。
- [ ] **验证**：用户 B 直接访问余额页 → 后端 `403`，App 显示明确错误态（不是空白页，也不得静默失败）。

### 步骤 7：扫码（AC-M4）

- [ ] `mobile/app/(app)/scan.tsx`：`expo-camera` 的 `CameraView` + `barcodeScannerSettings`。
- [ ] 用 `useCameraPermissions()` 申请相机权限，被拒时给出可操作提示。
- [ ] 扫到的字符串 → 作为 `document_number` 查询 → **命中**跳明细；**未命中**（后端 `200` + 空列表）显示明确提示。
- [ ] **验证**：Android **真机** Expo Go 上真实扫码（模拟器不支持 `expo-camera`）。

### 步骤 8：跨端纪律复核

- [ ] `mobile/` 不 import `frontend/**`；`frontend/` 不 import `mobile/**`。
- [ ] 未引入 `expo-notifications` / `expo-sqlite`。
- [ ] `mobile/` **真实 import** `@repo/domain` 与 `@repo/tokens`（父任务 AC5 的前提——只声明依赖不算）。
- [ ] 门禁脚本 `scripts/check-cross-platform-boundaries.mjs` 通过。
- [ ] 上端矩阵中 `inventory` 的 `app_scope` 与实际实现的页面一致。

## Validation Commands

```bash
# 共享层与门禁
bun test scripts/check-cross-platform-boundaries.test.ts
bun test scripts/check-thin-routes.test.ts

# Web 不得回归（AC-M7）
bun run build
bun run lint
python hooks/run_quality_hooks.py --json

# App
bun run --filter mobile start
```

## Review Gate

- AC-M1 ~ AC-M7 全部满足。
- 父任务 E2E-001 ~ E2E-008 执行完毕，结论记入 Validation Notes。
- **AC-M3 必须包含服务端拒绝的实证**（`403`），仅有前端隐藏入口不算通过。
- **AC-M4 必须在 Android 真机执行**；模拟器结果不作为通过依据。

## Rollback Points

| 点 | 回滚方式 |
|---|---|
| 步骤 1 后 Metro 无法解析 workspace 包 | 加 `watchFolders` / `nodeModulesPaths`；仍失败则把 `mobile/` 暂时移出 workspace 单独装依赖（记录为已知限制） |
| 步骤 2–4 后登录链路不通 | 回退 `mobile/` 到骨架状态；共享层不受影响 |
| 步骤 7 扫码不可用 | 扫码是 AC-M4 的核心，不可降级为"手动输入"通过；若真机不可用，记录具体阻塞项并保持 AC-M4 未满足 |

**关键保证**：本任务全部改动在 `mobile/` 与少量根配置内，不触及 `frontend/` 业务代码，因此任一阶段失败都不会回归 Web。

## Validation Notes

（执行时在此记录命令输出、真机验证结论与任何环境阻塞项）
