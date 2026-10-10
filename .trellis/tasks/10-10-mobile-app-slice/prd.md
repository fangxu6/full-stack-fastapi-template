# React Native App 落地（Expo 登录 + 库存只读 + 扫码）

## Goal

在 `mobile/` 建立 Expo 工程并接入共享内核：登录（`expo-secure-store` 存 token）、库存单据列表/明细与库存余额只读页面（复用同一契约与 RBAC 权限语义）、扫单据号定位单据的扫码流程。以 Android 真机 Expo Go 验收。

## Background

父任务 `10-10-react-native-app` 持有 D1–D8 决策与全部仓库证据：

- 决策：[父任务 prd.md](../10-10-react-native-app/prd.md)
- 技术设计：[父任务 design.md](../10-10-react-native-app/design.md)

**前置依赖**：本任务**依赖 `10-10-cross-platform-kernel` 完成**。在它交付 `@repo/contract`、`@repo/domain`、`@repo/tokens` 之前，本任务不得启动——本任务需要的共享层尚不存在。

已核实的环境与后端事实：

- 本机为 Windows 10，**无 Android SDK / adb / gradle / Android Studio**，也无 Xcode（见父任务 prd.md「开发机环境」）。
- Expo Go 已确认包含 `expo-secure-store` 与 `expo-camera`（含条码扫描）；**不含**远程推送（`expo-notifications`）。扫码需真机，模拟器不支持 `expo-camera`。
- 后端**没有任何条码字段**；`GET /api/v1/inventory/documents` 支持 `document_number` 过滤（`max_length=64`）。
- `GET /api/v1/inventory/balances/{raw,finished}` 只支持 `item_name` 与 `processing_unit_id`，**不支持 `item_code`**。
- `inventory.documents.read` 与 `inventory.balances.read` 是**两个不同权限码**。

## Requirements

- **M1**：`mobile/` 使用 Expo（expo-router），可通过 Expo Go 在 Android 真机启动，**无需本机 Android SDK**。
- **M2**：登录复用生成 SDK（`LoginService.loginAccessToken`），token 存入 `expo-secure-store`，**不得使用 `localStorage`**。
- **M3**：通过 `configureApiClient` 注入 `baseUrl`、`getToken`（**异步**读 SecureStore）、`onAuthFailure`（跳登录页）。
- **M4**：查询层复用 `@repo/domain` 的 `myPermissionsQueryOptions`、`classifyPermissionQueryError`、`createQueryClient` 与 inventory 查询函数；**不得在 App 内重写 URL 或 query 参数映射**。
- **M5**：单据列表页按 `document_number` 查询；单据明细页按单据 id 查询。
- **M6**：库存余额只读页。
- **M7**：首页入口按 `hasPermission()` 过滤：无 `inventory.documents.read` 不显示单据入口；无 `inventory.balances.read` 不显示余额入口。
- **M8**：扫码页用 `expo-camera` 的 `CameraView` + `barcodeScannerSettings` 扫单据号 → 跳单据列表/明细；**未命中必须给出明确提示**（后端对未知单据号返回 `200` + 空列表，不是错误）。
- **M9**：`mobile/` 不得 import `frontend/**`；不得引入 `expo-notifications` 或 `expo-sqlite`。
- **M10**：iOS 兼容性纪律——不得写 iOS 明确不兼容的代码（D4 是范围决策，不是技术锁定）。
- **M11**：提供 `btoa` 兜底 polyfill（Hermes 无 `btoa`/`Buffer`），且**不得使用 Basic Auth**。
- **M12**：不得新增或修改后端接口与字段（Out of Scope）。

## Acceptance Criteria

- [ ] **AC-M1**（= 父 AC2）：App 在本机启动并完成登录（真实后端 JWT），token 存于 `expo-secure-store`。
- [ ] **AC-M2**（= 父 AC3）：至少一个真实业务页面从后端取数并正确渲染，且复用与 Web 同源的 API 契约。
- [ ] **AC-M3**（= 父 AC4）：无权限时不展示入口；**服务端拒绝仍然生效**（`403`）。
- [ ] **AC-M4**（= 父 AC9）：Android 真机（Expo Go）扫码可用；扫到的单据号能返回真实数据，或给出明确的「未命中」提示；全程不依赖任何后端字段/接口新增。
- [ ] **AC-M5**：`mobile/` 中不存在 `/api/v1/` 字符串字面量（URL 全部来自 `@repo/domain`）——门禁规则 4。
- [ ] **AC-M6**：`mobile/` 不 import `frontend/**`，且 `frontend/` 不 import `mobile/**`。
- [ ] **AC-M7**：现有 Web 构建与校验仍通过（`bun run build`、`bun run lint`、`check-thin-routes`）——引入 App 不得回归 Web。

## Out of Scope

- 离线缓存（`expo-sqlite`）与远程推送（`expo-notifications`）——D6 已排除。
- iOS 构建、签名、EAS 配置。
- 应用商店上架与 CI/CD 发布流水线。
- 后端接口/字段新增。
- Web 功能的全量移动端对等迁移。

## Notes

- 本任务覆盖父任务的 **AC2、AC3、AC4、AC9**。
- **依赖** `10-10-cross-platform-kernel`。
- E2E：本任务执行父任务 [e2e-api-tests.md](../10-10-react-native-app/e2e-api-tests.md) 的 **E2E-001 ~ E2E-008**。本任务自己的 [e2e-api-tests.md](e2e-api-tests.md) 只写 App 侧执行条件与前置数据，**不重复定义用例**。
