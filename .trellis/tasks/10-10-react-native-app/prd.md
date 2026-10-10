# 长期跨端开发方案：开发 Web 时如何同时实现移动端

## Goal

建立一套长期可持续的跨端开发方案，使得在开发 Web 端功能时，能以可预期的成本**同时**交付移动端（React Native），而不是把 App 当作事后追加的第二套系统。

用户明确要的不是"一次性加个 App"，而是一个**长期方案**：Web 与移动端的并行开发模式、复用边界与交付纪律。

## Background

### 用户诉求

- 当前只有 Web 前端可用。
- 需要追加 App 功能，技术选型指定为 React Native。
- 关键诉求：**长期方案** —— 开发 Web 端时，如何同时实现移动端。

### 已确认事实（仓库证据）

**前端（Web）现状**

- 技术栈：React 19 + Vite 8 + TanStack Router + TanStack Query + Tailwind 4 + Radix UI + antd 6。
- 分层边界已确立且被 spec 强制：`app/*`（shell/导航/守卫）、`platform/*`（auth、docs、system）、`features/*`（items、inventory、scheduler）、`shared/*`（跨域复用）、`routes/*`（薄路由）。
  - 证据：`frontend/ARCHITECTURE.md`、`.trellis/spec/frontend/directory-structure.md`
- 分层有自动校验脚本：`scripts/check-thin-routes.mjs`（含测试 `scripts/check-thin-routes.test.ts`）。
- antd 只被 11 个文件使用（`app/providers/AntdProvider.tsx` 及 inventory / scheduler / system / docs / excel 相关页面），是典型的"后台表格型"依赖：
  - 证据：`grep -rln "from \"antd\"" frontend/src` → 11 个文件
  - 主题配置：`frontend/src/app/providers/AntdProvider.tsx`（`colorPrimary: #0f766e`、`borderRadius: 8`、cssVar key `fastapi-template`）
- API 客户端是**生成产物**：`@hey-api/openapi-ts` 0.73.0，输入 `frontend/openapi.json`，输出 `frontend/src/client`，使用 `legacy/axios` + `@hey-api/sdk`（`asClass: true`）+ `@hey-api/schemas`。
  - 证据：`frontend/openapi-ts.config.ts`、`scripts/generate-client.sh`
  - `core/request.ts` 依赖 axios 与浏览器全局（`btoa`、`Blob`、`FormData`）。
- 已存在"平台无关"的候选逻辑层（可直接成为共享包内容）：
  - `frontend/src/shared/permissions/index.ts` —— `PermissionCode` 联合类型（15 个权限码）+ `hasPermission()` + `isSafeInternalPath()`，纯函数、无 DOM 依赖。
  - `frontend/src/app/permissions.ts` —— `myPermissionsQueryOptions`（queryKey `["iam","permissions"]`、`staleTime: 30_000`）、`classifyPermissionQueryError()`、`readMyPermissionsForRoute()`，只依赖 TanStack Query + 生成客户端。
  - `frontend/src/app/query-client.ts` —— 认证失效判定与 `clearAuthState()`（其中 `localStorage` 与 `window.location` 是 Web 专属）。
  - `frontend/src/app/router/guards.ts` —— `requireLogin()` / `requirePermission()`，与 TanStack Router 耦合。
- 认证态存储依赖浏览器 `localStorage`：`platform/auth/hooks/useAuth.ts:16,46`、`main.tsx:16`、`app/query-client.ts:6`、`shared/components/theme/ThemeProvider.tsx:38,96`。
- 设计令牌目前以 CSS 变量 + Tailwind `@theme inline` 形式存在于 `frontend/src/index.css`（`--primary`、`--radius`、`--color-*` 等 oklch 值），**没有**平台中立的令牌源。
- 现有业务页面规模（迁移成本参考）：`InventoryCorrectionsPage.tsx` 578 行、`InventoryDocumentsPage.tsx` 578 行、`InventoryMastersPage.tsx` 293 行、`InventoryBalancesPage.tsx` 217 行；`ItemsPage.tsx` 57 行。
- 部分业务数据访问绕过生成客户端直接调用 `request()`：`frontend/src/features/inventory/api.ts:1-40`。

**后端现状**

- FastAPI + SQLModel + PostgreSQL，分层为 `api/*`、`services/*`、`crud/*`、`models/*`、`schemas/*`、`core/*`、`infra/*`、`modules/*`。
  - 证据：`backend/ARCHITECTURE.md`
- 认证是 OAuth2 password flow，返回 Bearer JWT，天然适配移动端：
  - `backend/app/api/routes/login.py:19-24`（`POST /login/access-token`）
  - `backend/app/api/routes/login.py:27-29`（`POST /login/logout`）
- 已有请求级 `X-Request-ID`、统一异常处理与结构化错误响应（含 `request_id`）。
  - 证据：`ARCHITECTURE.md` 第 7 节、`backend/app/core/exceptions.py`
- 权限模型是服务端校验的 RBAC（`permission_required`），含 `system.users.*` / `iam.roles.*` 治理权限概念。
  - 证据：`backend/app/modules/iam/dependencies.py`、`CONTEXT.md`

**仓库与工程化现状**

- 根 `package.json` 是 bun workspace，但 `workspaces` 目前**只有 `frontend`**，没有共享包层。
- 无任何移动端痕迹：全仓库（排除 node_modules/.git/.venv）搜索 `react-native` / `expo` / `移动端` / `mobile app` 均无命中。
- `docs/` 与 `.trellis/` 中没有任何 App / 移动端需求、路线图或规格条目；`docs/3-month-roadmap.md` 六期规划全部是 Web 与后端内容。
- 部署现状为 Docker Compose + Traefik（`compose.yml`、`compose.traefik.yml`），无移动端构建/分发链路。
- `.trellis/spec/` 已有 `frontend/`、`backend/`、`templates/` 三层规格，但**没有**跨端/共享层规格，也没有针对"新功能必须两端同时落地"的交付约束。
- 根 `package.json` 的脚本以 `--filter frontend` 驱动（`dev`/`lint`/`test`/`test:ui`）；新增共享包或工程需要同步这些入口。
- `frontend/tsconfig.json` 使用 `moduleResolution: "bundler"`、`paths: { "@/*": ["./src/*"] }`，并对 `tsconfig.node.json` 使用 project references；共享包需要相应的引用与路径配置。
- 生成客户端是**已提交入库**的产物（`git ls-files frontend/src/client` → 10 个文件、共 5706 行），不是构建期临时生成：`core/request.ts`(346)、`schemas.gen.ts`(2513)、`sdk.gen.ts`(1611)、`types.gen.ts`(1004) 及 5 个 core 文件。
- `frontend` 直接依赖 `axios@1.19.0`（精确版本）与 `zod@^4.4.3`；`@hey-api/openapi-ts@0.73.0` 为 devDependency。共享层若复用 axios/zod，需要先决定依赖归属。
- 前端 lint/format 统一使用 Biome（`biome check --write --unsafe`），共享包需要纳入或排除其检查范围。
- 生成链路为 `scripts/generate-client.sh`：后端导出 `frontend/openapi.json` → `bun run --filter frontend generate-client` → `scripts/normalize-generated-client-whitespace.mjs frontend/src/client` → `biome ci`。若生成物迁出 `frontend/`，此脚本必须同步修改。

### 存量系统参考（zqsystem）

用户提供了对另一系统 `D:\Workspace\sts\zqsystem` 的跨端实现分析，已逐行核验属实（详见同目录 `research-zqsystem-cross-platform.md`）：

- 该系统 App 为 **Cordova WebView 混合**（`js/mobileApp`，RequireJS + Backbone + Zepto + Cordova 插件），Web 为**多个相互独立的前端项目**（`generationPC`、`generationMobile`、`officialWeb`、`niuqiClient`、`managementPlatform`、`systemPlatform` 等 10 个维护中项目）。
- 跨端共享**只有后端 HTTP 接口**（`/stockTrade/queryOrderList`、`/h5/userInfo` 被 2~3 个前端各自直连、各自解析），**没有**共享类型、校验层、权限语义层或 UI 组件包。
- 端内复用存在且显式（App 用 RequireJS 模块 + Velocity `#parse`；Web 用 `layout/*.vm`）；跨端 UI 复用不存在。
- 存在按 User-Agent 分流（`NiuqiPCController.java:841-845`），说明"一份页面适配所有端"最终退化为按端分流。
- 前端项目数量失控：10 维护中 + 4 已废弃 + 2 不维护 + 2 "未知项目"。

**对本次决策的意义**：该系统的技术栈（Cordova/jQuery/Velocity）不可迁移，但它提供了三条可参考的判断（契约是唯一长期稳定的跨端共享层；两端独立 UI 在工程上可持续；端内复用必须显式化）与两条必须规避的失败模式（未治理的接口级重复；前端项目数量失控）。

### 开发机环境（本机实测）

- 操作系统：**Windows 10**（`MINGW64_NT-10.0-26300`，MSYS/MinGW 64）；非 macOS。
- Node `v24.12.0`，Bun `1.4.2`。
- JDK：Zulu OpenJDK **17.0.15**（`JAVA_HOME=D:\scoop\apps\zulu17-jdk\current`）。
- Android 工具链**缺失**：`ANDROID_HOME` 与 `ANDROID_SDK_ROOT` 均为空；标准安装目录 `%LOCALAPPDATA%\Android\Sdk` 不存在；`adb`、`gradle` 不在 PATH；未安装 Android Studio。
- iOS 工具链**在本机不可能存在**：`xcodebuild` 不存在，Xcode 仅运行于 macOS。

**含义**：本机无法本地构建 iOS；Android 本地构建需先安装 Android Studio/SDK。因此 RN 工程形态（Q3）必须优先考虑"零原生工具链起步"与"云端构建 iOS"的可行性。

### Expo Go 能力边界（已核实）

经查 Expo 官方文档（SDK 57）：

| 能力 | 模块 | Expo Go 可用 |
|---|---|---|
| 安全存储 | `expo-secure-store` | ✅ 是（`requireAuthentication` 生物识别选项在 Expo Go 中不可用） |
| 相机 | `expo-camera` | ✅ 是（仅真机；模拟器/模拟机不可用） |
| 条码扫描 | `expo-camera` 的 `CameraView` + `barcodeScannerSettings` | ✅ 是（`expo-barcode-scanner` 为旧包，已被 `expo-camera` 取代） |
| 本地 SQLite | `expo-sqlite` | ✅ 是（**SQLCipher 加密不支持 Expo Go**） |
| 键值存储 | `expo-sqlite/kv-store` 或 `@react-native-async-storage/async-storage` | ✅ 是 |
| 远程推送 | `expo-notifications` | ❌ 否 —— Android SDK 53 起远程推送在 Expo Go 中不可用，需 development build；本地通知仍可用 |

**含义**：登录安全存储（R9）、条码扫描、离线 SQLite 缓存**都可在 Expo Go 阶段完成**，无需 Expo 账号或 Android SDK；**只有远程推送**会触发 development build 需求。这显著缩小了 Q6 各选项之间的成本差异。

### 由此推出的技术约束

1. 生成客户端目前不是"跨端中立"的：axios 可在 RN 运行，但 `core/request.ts` 的浏览器全局依赖与 `localStorage` 认证态在 RN 上不可用。复用契约需要先抽出平台无关层。
2. 现有 `frontend/*` 分层规则是 Web 专属（Tailwind、Radix、antd、TanStack Router 均为 Web/DOM 依赖），不能直接搬到 RN；但其中 `shared/permissions` 与 `app/permissions` 已接近平台无关。
3. 当前 bun workspace 只有 `frontend`；若要真正复用类型与契约，需要引入共享包层（例如 `packages/*`），这会改变仓库根结构。
4. 设计令牌没有单一真相源（只有 `index.css` 里的 CSS 变量），跨端主题一致性目前无法自动保证。
5. 后端无需为 App 做认证改造即可支持移动端（Bearer JWT + RBAC 已就绪）。
6. 仓库已有的 spec/校验机制（`.trellis/spec/*`、`scripts/check-thin-routes.mjs`）是"把架构约束变成可执行门禁"的现成范式，跨端交付纪律应复用这一范式而不是另起一套。

## 已决策

- **D1（对应 Q1，已确认 = A）跨端复用策略：共享领域内核 + 各端独立 UI。**
  - 内容：`packages/contract`（OpenAPI 生成物 + 平台中立的请求层，token 存储由宿主注入）、`packages/domain`（权限码与判定、query key、校验、错误分类、headless 业务规则）、`packages/tokens`（设计令牌单一真相源）由两端共享；Web 保留 Tailwind/Radix/antd，App 使用 RN 组件库。
  - 诚实预期：**内核一次 + UI 两次**，而非"写一次"。收益在于把两次 UI 之间的差异压缩到纯呈现层。
  - 未选项及原因：B（单代码库 + react-native-web）需重写现有 Web UI 并牺牲 antd 后台表格体验（本仓库有 578 行的 inventory 页面）；C（仅共享 OpenAPI 类型）等于 zqsystem 现状，已被证明会走向未治理重复与项目数量失控。
  - 证据：`research-zqsystem-cross-platform.md`（R-a 契约是唯一长期稳定的共享层、R-b 两端独立 UI 可持续、R-e 反证 B）；本仓库 `frontend/src/shared/permissions` 与 `frontend/src/app/permissions` 已接近平台无关，是现成的共享层起点。
- **D2（对应 Q2，已确认 = A）共享层边界与仓库结构：`packages/*` 三包 + `mobile/` 工程。**
  - 目标布局：`backend/`（不变）、`frontend/`（Web，不变）、`mobile/`（新增 RN）、`packages/{contract,domain,tokens}/`。
  - 依赖方向（可机器校验）：`frontend → domain → contract`、`mobile → domain → contract`、`frontend → tokens`、`mobile → tokens`；`frontend` 与 `mobile` **不得互相引用**。
  - 包边界约束：`contract` 不依赖任何 UI 库或 DOM；`domain` 不依赖 `react-dom` / `react-native` / `antd` / Tailwind；`tokens` 无运行时依赖。
  - 子决定 1（生成物归属）：OpenAPI 生成物落到 `packages/contract/src/generated`，不再留在 `frontend/src/client`；`scripts/generate-client.sh` 与 `scripts/normalize-generated-client-whitespace.mjs` 必须同步修改（现硬编码 `frontend/src/client`）。
  - 子决定 2（目录命名）：App 放 `mobile/`，与 `backend/`、`frontend/` 平级扁平命名一致；不引入 `apps/*` 二次分层。
  - 子决定 3（请求层拆分）：`frontend/src/client/core/request.ts`（346 行，axios）拆为"平台中立核心 + 宿主注入适配"；token 存储、baseURL、认证失效处理由宿主注入（Web 注入 `localStorage`，App 注入安全存储）。
  - 子决定 4（首批迁入内容，用于满足 AC5"真实被引用"）：`frontend/src/shared/permissions/index.ts`（15 个 `PermissionCode` + `hasPermission`）与 `frontend/src/app/permissions.ts` 的 `classifyPermissionQueryError` → `packages/domain`；`frontend/src/index.css` 的设计令牌 → `packages/tokens`（生成 Web CSS 变量与 RN theme）。
  - 未选项及原因：B（单一 `packages/core`）边界只能靠目录约定，无法用工具禁止 domain 依赖 antd，长期退化为杂物包；C（TS path alias 跨工程引用）使 `mobile` 与 `frontend` 互相耦合、Metro 解析困难，违背 D1"两端独立"。
  - 证据：仓库已有"把架构约束变成可执行门禁"的范式（`scripts/check-thin-routes.mjs` + `scripts/check-thin-routes.test.ts`），三包使依赖方向可被机器校验；三部分变更来源与频率不同（contract 为生成物、domain 为手写语义、tokens 为设计令牌），分包保证"重生成不污染手写代码"，即 `research-zqsystem-cross-platform.md` N-c 的解药。
- **D3（对应 Q3，已确认 = A）RN 工程形态：Expo。**
  - 内容：`mobile/` 使用 Expo（Expo SDK + expo-router）；开发以 Expo Go 起步（手机扫码，零原生工具链）；需要原生能力或 iOS 产物时切换 development build；iOS 通过 EAS 云构建（云端 macOS runner）产出，无需 Mac。
  - 保留退路：需要自定义原生代码时执行 `expo prebuild` 生成 `android/`/`ios/` 工程（即"Expo + prebuild"形态），因此该决定不是不可逆的。
  - 未选项及原因：B（bare React Native CLI）需先安装 Android Studio + Android SDK 才能跑第一行代码，且本机（Windows）无法本地构建 iOS，与"低摩擦并行开发"目标冲突；C（Expo + 立即 prebuild）一开始就要维护原生工程，RN 升级需手动 merge，且失去 Expo Go 的零配置体验。
  - 证据：本机实测无 Android SDK/adb/gradle/Android Studio 且无 Xcode（见"开发机环境"）；Expo 官方文档明确支持 Bun workspace monorepo、会自动检测并配置，Metro 的 `watchFolders`/`nodeModulesPaths` 由 `expo/metro-config` 处理，直接消解 D2 中标注的 Metro 接线成本；EAS Build 可在 Windows 上构建 iOS。
  - 已知代价（**已核实并更正**）：Expo Go 的模块集合固定，但经查证官方文档（SDK 57），**相机（`expo-camera`）、条码扫描、安全存储（`expo-secure-store`）、本地 SQLite（`expo-sqlite`）均包含在 Expo Go 中**；**唯一**需要 development build 的能力是**远程推送（`expo-notifications`，Android SDK 53+）**。因此 Expo Go 阶段的能力边界比最初判断宽，需要 development build 的概率显著更低。详见"Expo Go 能力边界（已核实）"。
- **D4（对应 Q4，已确认 = C）目标平台：只做 Android。**
  - 内容：本迭代以 Android 为唯一验收平台（Expo Go 真机验证，零原生工具链）；**不配置任何 iOS 构建**（不设 iOS bundle identifier、不在 `eas.json` 配置 iOS profile、不做 iOS 验证）；分发采用内部分发（APK 直装或 EAS internal distribution），不做应用商店上架。
  - 诚实说明（范围而非技术限制）：Expo/RN 代码天然双端，`mobile/` 仍可在 iOS 上运行；"只做 Android"是**范围与验收决策**，不是技术锁定。因此须遵守一条纪律：不得写 iOS 明确不兼容的代码，以免未来补 iOS 时被迫重写（该条进 `.trellis/spec/`）。
  - 对 D3 的影响：D3 中"iOS 通过 EAS 云构建"这一理由不再适用，Expo 的保留理由变为**零原生工具链起步（Expo Go 真机）+ Bun workspace monorepo 原生支持**；结论不变。
  - 未选项及原因：A（Android 优先 + iOS 保持可构建）需额外维护 iOS 可构建状态却无验收价值；B（双端同等优先）需 Apple Developer 账号（$99/年）与 EAS iOS 签名配置，且本机无法本地调试 iOS，本迭代周期显著变长。
  - 后果（已知代价）：放弃 iOS 用户；未来补 iOS 需重走 EAS + Apple 账号 + 签名全流程。
- **D5（对应 Q5，已确认 = A）交付纪律：强制共享内核 + 显式上端决策，不强制 UI 对等。**
  - "同时实现"的操作定义：**同时可复用（内核）+ 同时被决策（上端矩阵）**，而不是同时被实现（UI 对等）。
  - 强制 1（内核共享）：新接口必须进 `packages/contract`；权限码、query key、校验、错误分类、业务规则必须进 `packages/domain`；设计令牌必须进 `packages/tokens`。违反则门禁失败。
  - 强制 2（上端决策）：每个功能必须显式声明上端策略（Web only / App only / both），不允许"未考虑移动端"。
  - 不强制：UI 对等。App 只实现适合移动端的功能子集。
  - 落地物：`.trellis/spec/cross-platform/*` 规格 + 门禁脚本（沿用 `scripts/check-thin-routes.mjs` + `scripts/check-thin-routes.test.ts` 范式）。
  - 未选项及原因：B（同迭代功能对等）在本仓库会强制产出无价值的移动端页面（inventory 四个页面 217~578 行、antd 表格 + excel 导入导出、scheduler 定时任务、iam 治理页均属后台管理型），且并未消除增长失控，只是把失控转移到移动端；C（移动优先）与现有 Web 为主的团队习惯冲突，且 Expo Go 阶段不足以承载主要业务。
  - 证据：A 精准消除 `research-zqsystem-cross-platform.md` 的两个失败模式——N-c（未治理的接口级重复）由"强制共享契约 + 领域语义"消除，N-d（前端项目/功能无限增长）由"显式上端决策"消除。
  - 代价：需接受"某些功能永远不上 App"，并维护上端矩阵与门禁脚本。
- **D6（对应 Q6，已确认 = B）首批上 App 的功能：只读 + 扫码。**
  - 内容：`mobile/` 首批交付 = 登录（`expo-secure-store` 存 token）+ 库存只读页面 + 条码扫描（`expo-camera` 的 `CameraView` + `barcodeScannerSettings`，Expo Go 可用）。不做离线缓存，不做远程推送。
  - 未选项及原因：A（零设备能力）范围过窄，未验证"移动端为何存在"的核心场景；C（含离线）需设计离线数据模型与同步/冲突策略，且后端无离线接口，会把两个未验证变量叠加。
  - **关键发现（扫码可行性）**：后端**完全没有条码字段**（`grep -rni "barcode|条码|scan_code" backend/app --include=*.py` → 无匹配）。库存域实际字段为 `item_name`(品名)、`item_code`(货号)、`wool_content`(含毛量)、`document_number`(单据号)、`color_code`(色号)、`dye_lot_no`(缸号)。
  - **关键约束**：`GET /inventory/balances/{raw,finished}` **只支持 `item_name` 与 `processing_unit_id` 过滤，不支持 `item_code`**；`GET /inventory/ledger` 需要 5 段复合键（`item_name` + `item_code` + `wool_content` + `processing_unit_id` + `ledger_kind`）。因此"扫一个码直接查出库存行"在当前后端能力下**不成立**，除非约定码内容为结构化标签。
  - 可用端点与权限（证据：`backend/app/modules/inventory/router.py`）：`GET /inventory/documents`（`inventory.documents.read`，支持 `document_number` 过滤）、`GET /inventory/documents/{id}`（`inventory.documents.read`）、`GET /inventory/balances/raw|finished`（`inventory.balances.read`）、`GET /inventory/ledger`（`inventory.ledger.read`）、`GET /inventory/suggestions`（`inventory.documents.read`）、`GET /inventory/{processing,receiving}-units`（`inventory.masters.read`）。
  - 结论：扫码目标必须显式决定（见 Q7）。D6 **不包含**任何后端字段或接口新增。
- **D7（对应 Q7，已确认 = A）扫码目标：单据号（`document_number`）。**
  - 内容：App 扫码 = 扫单据号 → `GET /api/v1/inventory/documents?document_number=X`（列表）→ 选中 → `GET /api/v1/inventory/documents/{id}`（明细）。权限码 `inventory.documents.read`。
  - 为什么是它：唯一同时满足"后端零改动"（守住 Out of Scope）、"扫码语义无歧义"（`document_number` 是 `max_length=64` 的单一字符串）、"有完整列表 + 详情链路"的组合；且其权限码 `inventory.documents.read` 与库存余额的 `inventory.balances.read` 是**两个不同权限码**，可真实检验 AC4 的权限差异，而不是只测一个权限码。
  - 未选项及原因：B（扫品名 → balances）依赖标签上印的是品名，且 balances **不支持 `item_code`**，扫货号无效；C（扫结构化二维码 → ledger）需先约定码内容格式，且 ledger 需 5 段复合键，二维码必须承载全部 5 段，前提是现有标签已是该格式（无法从代码得知）；D（扫任意码填入搜索框）不保证命中，价值最弱。
  - 未命中处理：单据号查无结果时必须给出**明确提示**，不得静默失败（对应 AC9）。
  - 证据：`backend/app/modules/inventory/router.py`（`/documents` 支持 `document_number` 过滤；`/documents/{document_id}` 为详情端点）；`backend/app/schemas/inventory.py`（`document_number: str = Field(min_length=1, max_length=64)`）。

- **D8（对应 Q8，已确认 = B）任务形态：父任务 + 2 个子任务。**
  - 父任务 `10-10-react-native-app`：持有完整需求集、任务地图、**跨子任务验收项（AC5）**、最终集成复核。本身不直接实现代码。
  - 子任务 `10-10-cross-platform-kernel`（共享内核落地）：`packages/{contract,domain,tokens}` + 生成物迁移 + 规格/钩子/biome/生成脚本同步 + 门禁脚本 + 上端矩阵 + 跨端规格。覆盖 **AC1、AC6、AC7、AC8**。
  - 子任务 `10-10-mobile-app-slice`（App 落地）：`mobile/` Expo 工程 + 登录（`expo-secure-store`）+ 单据列表/明细 + 库存余额只读 + 扫码 + RBAC 入口过滤。覆盖 **AC2、AC3、AC4、AC9**。**依赖子任务 1 完成。**
  - AC5（"共享层被两端真实引用"）**留在父任务**：它要求 Web 与 App 两端同时存在，天然是跨子任务的集成验收项，无法在任一子任务内单独验证。
  - 未选项及原因：A（单任务 P1→P6 顺序推进）会产生一条超长变更历史，且 P1 是全任务唯一的破坏性重构（改 38 个消费者的依赖来源 + 15 份规格 + 2 处钩子 + biome + 1 个生成脚本）；一旦 P1 出问题，App 工作已被牵连，回滚不干净。
  - 理由：AC5 的集成性质说明本任务**本来就是集成型任务**；把破坏性重构隔离为有明确出口（`bun run build` + `bun run lint` + `python hooks/run_quality_hooks.py --json` 全绿）的子任务，能让风险止步于该子任务。
  - 代价：多 2 个任务目录与一次子任务间交接；AC 分散在 3 处，追踪成本上升。

## Requirements

- R1：跨端复用策略（UI 统一程度）——**已决策 Q1 = A**，见"已决策 D1"。
- R2：共享层边界与仓库结构（`packages/*` 的划分与依赖方向）——**已决策 Q2 = A**，见"已决策 D2"。
- R3：RN 工程形态与框架方案（Expo / bare RN CLI）——**已决策 Q3 = A（Expo）**，见"已决策 D3"。
- R4：目标平台与发布/分发方式——**已决策 Q4 = C（只做 Android）**，见"已决策 D4"。
- R5："新功能如何同时落两端"的交付纪律与规格（写入 `.trellis/spec/`）——**已决策 Q5 = A**，见"已决策 D5"。
- R6：App 必须复用后端既有认证（Bearer JWT）与 RBAC 权限语义，不得在客户端复制权限判定逻辑。
- R7：App 必须复用 API 契约（OpenAPI 生成物或从中抽取的平台无关层），不得手写第二套接口定义。
- R8：不得破坏现有 Web 分层约束与 `scripts/check-thin-routes.mjs` 校验。
- R9：App 端认证态存储必须使用移动端安全存储，不得使用 `localStorage`。
- R10：设计令牌需要有平台中立的单一真相源，使两端主题可对齐（在 Q1 选定后确定落地方式）。
- R11：App 扫码能力必须映射到后端**现有**查询参数（`document_number` / `item_name` 等），不得为此新增后端字段或接口（与 Out of Scope 一致）；"后端无条码字段"这一事实必须在设计中显式处理，不得假设存在条码字段。

## Acceptance Criteria

- [ ] AC1：跨端复用策略与共享层边界有明确文档，且依赖方向可被机器校验（或至少可被审查）。
- [ ] AC2：App 工程可在本机启动并完成登录（真实后端 JWT），token 存储于移动端安全存储。
- [ ] AC3：App 至少一个真实业务页面从后端取数并正确渲染，且复用与 Web 同源的 API 契约。
- [ ] AC4：App 使用后端 RBAC 语义（无权限时不展示入口，且服务端拒绝仍然生效）。
- [ ] AC5：共享层被两端真实引用（不是"建了目录没人用"），且 Web 侧引用共享层后行为不变。
- [ ] AC6：现有 Web 构建与校验全部仍然通过（`bun run build`、`bun run lint`、`scripts/check-thin-routes.mjs`）。
- [ ] AC7：`.trellis/spec/` 中存在跨端交付规格，说明新功能如何同时落两端。
- [ ] AC8：仓库文档（`ARCHITECTURE.md` 及/或前端文档）反映新增的 App 边界与复用策略。
- [ ] AC9：App 扫码流程在 Android 真机（Expo Go）可用；扫到的码经映射后能返回真实数据，或给出明确的"未命中"提示；全过程不依赖任何后端字段/接口新增。

## Out of Scope

- 后端业务接口的新增或语义变更（除非落地时发现真实缺口，另行开任务）。
- 应用商店上架、签名证书、CI/CD 发布流水线（除用户明确要求纳入本次范围）。
- 现有 Web 功能的全量移动端对等迁移（除用户明确要求）。

## Open Questions

设计树（按依赖排序，同轮只问可立即回答的节点）：

- （Q1 已决策 = A，见"已决策 D1"；以下为其下游节点）
- （Q2 已决策 = A，见"已决策 D2"）
- （Q3 已决策 = A（Expo），见"已决策 D3"）
- （Q4 已决策 = C（只做 Android），见"已决策 D4"）
- （Q5 已决策 = A，见"已决策 D5"）
- （Q6 已决策 = B（只读 + 扫码），见"已决策 D6"）
- （Q7 已决策 = A（扫单据号），见"已决策 D7"）
- （Q8 已决策 = B（父任务 + 2 子任务），见"已决策 D8"）
