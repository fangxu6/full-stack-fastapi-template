# 跨端共享内核落地（packages/contract + domain + tokens）

## Goal

建立 `packages/{contract,domain,tokens}` 三个共享包，把 Web 现有的生成契约、平台中立领域语义与设计令牌抽为**跨端单一真相源**；Web 侧保留再导出 shim 以保证行为完全不变。

本任务只做「内核落地 + 治理门禁」，**不做 App**。

## Background

父任务 `10-10-react-native-app` 持有 D1–D8 决策与全部仓库证据：

- 决策：[父任务 prd.md](../10-10-react-native-app/prd.md)
- 技术设计：[父任务 design.md](../10-10-react-native-app/design.md)
- 外部系统参考：[research-zqsystem-cross-platform.md](../10-10-react-native-app/research-zqsystem-cross-platform.md)

本文件只写本子任务的需求与验收。以下前提均已在父任务核实：

- 生成物是**已提交入库**的产物（10 文件 / 5706 行），**38 个 Web 文件** import `@/client`（全部走 index 路径）；其中 **2 个额外** import 了深路径（`features/inventory/api.ts:10` → `@/client/core/request`；`shared/excel/excel.ts:2` → `@/client/core/ApiRequestOptions`），因此需要 3 个再导出 shim 而非 1 个。
- `frontend/src/app/query-retry.ts` 已验证平台中立（只依赖 `axios` + `ApiError`）。
- `frontend/src/features/inventory/api.ts` 绕过生成 SDK 手写 URL + query 参数映射——这是 zqsystem **N-c 失败模式**在本仓库的具体形态，也是本任务必须消除的对象。
- `.trellis/spec/frontend/route-permission-navigation-contract.md` 把权限真相源显式钉在 `shared/permissions/*` 与 `app/permissions.ts`，因此采用**再导出**而非删除原文件。
- `hooks/quality_hooks/frontend.py:17` 有生成路径允许列表；`frontend/biome.json:10` 排除 `**/src/client/**/*`。
- `frontend/src/app/query-client.ts` 混入了 Web 专属的 `localStorage` 与 `window.location`。

## Requirements

- **K1**：建立 `packages/contract`，`@hey-api/openapi-ts` 生成物落到 `packages/contract/src/generated`；`frontend/src/client/` 保留 **3 个**再导出 shim（`index.ts`、`core/request.ts`、`core/ApiRequestOptions.ts`），使 38 个消费者**零改动**。`packages/contract/src/index.ts` 必须显式再导出 `core/request`、`core/ApiRequestOptions`、`core/OpenAPI`、`core/ApiError`（生成物的 `index.ts` 默认不含）。
- **K2**：`scripts/generate-client.sh` 与 `scripts/normalize-generated-client-whitespace.mjs` 的调用点同步改为新路径；**重新生成后 `git diff` 必须为空**。
- **K3**：`packages/contract` 提供 `configureApiClient(host)` 接缝，`baseUrl` / `getToken` / `onAuthFailure` 由宿主注入；`OpenAPI.TOKEN` 保持**异步**签名（`expo-secure-store` 需要异步读取）。
- **K4**：建立 `packages/domain`，迁入：`PermissionCode` 与判定、`myPermissionsQueryOptions` + `classifyPermissionQueryError`、`query-retry`、inventory 查询参数映射、认证失效判定与 `createQueryClient({ onAuthFailure })`。
- **K5**：`packages/domain` **不得**依赖 `react-dom` / `react-native` / `antd` / `tailwindcss` / `@tanstack/react-router`；只导出纯函数、query options、query client 工厂与类型，**不含 JSX**。
- **K6**：Web 侧 `shared/permissions/index.ts` 与 `app/permissions.ts` 改为再导出；`readMyPermissionsForRoute()` 因依赖 Web 专属 `queryClient` 单例而**保留在 Web 侧**。
- **K7**：建立 `packages/tokens` 作为设计令牌单一真相源，生成 `frontend/src/index.css` 的托管块与 RN 主题；生成的 `:root` / `.dark` 必须与迁移前**字节级一致**。
- **K8**：新增 `scripts/check-cross-platform-boundaries.mjs` + `scripts/check-cross-platform-boundaries.test.ts`，实现父任务 design.md 第 3 节的 6 条规则；新增仓库根 `cross-platform.matrix.json`。
- **K9**：新增 `.trellis/spec/cross-platform/*`，写明新功能如何同时落两端（D5 强制 1 与强制 2）。
- **K10**：更新把**生成物位置**表述为 `frontend/src/client/**` 的规格与质量钩子路径；表述为「消费者从这里导入类型」的句子**无需修改**（再导出使其仍成立）。
- **K11**：根 `package.json` 的 `workspaces` 与脚本入口纳入新包；Biome 检查范围扩展到 `packages/*`。

## Acceptance Criteria

- [ ] **AC-K1**：`packages/{contract,domain,tokens}` 存在且被 bun workspace 识别（`bun install` 后可从 `frontend` 解析到 `@repo/*`）。
- [ ] **AC-K2**：`bash ./scripts/generate-client.sh` 成功后 `git diff --exit-code` 为空。
- [ ] **AC-K3**：`bun run build` 通过，且 38 个 `@/client` 消费者**未改动一行**（`git diff --stat` 中不出现这些文件）。
- [ ] **AC-K4**：`bun run lint` 通过。
- [ ] **AC-K5**：`python hooks/run_quality_hooks.py --json` 通过。
- [ ] **AC-K6**：`bun test scripts/check-cross-platform-boundaries.test.ts` 通过，且 6 条规则**各有正例与反例测试**。
- [ ] **AC-K7**：`bun test scripts/check-thin-routes.test.ts` 仍通过（未破坏既有门禁）。
- [ ] **AC-K8**：`packages/tokens` 生成的 `index.css` 托管块与迁移前 `:root` / `.dark` **字节级一致**。
- [ ] **AC-K9**：`packages/domain` 的 `package.json` 与源码不含被禁止依赖（由门禁规则 1、2 机器验证）。
- [ ] **AC-K10**：`.trellis/spec/cross-platform/*` 存在，且说明了「内核共享」与「上端决策」两条强制。
- [ ] **AC-K11**：Web 侧至少一个业务文件通过 `@repo/domain` 的**真实 API** 工作（不是仅再导出）——这是父任务 AC5 的前提条件。

## Out of Scope

- 任何 `mobile/` 代码（属子任务 `10-10-mobile-app-slice`）。
- 后端接口、字段、数据迁移。
- `AntdProvider` 硬编码主题值（`#0f766e` / `borderRadius: 8`）与令牌的合并——已知缺口，见父任务 design.md 第 6.3 节。
- iOS 相关配置。

## Notes

- 本任务覆盖父任务的 **AC1、AC6、AC7、AC8**。
- **必须在子任务 `10-10-mobile-app-slice` 之前完成**（后者依赖本任务产出的 `@repo/contract` 与 `@repo/domain`）。
- E2E：本任务执行父任务 [e2e-api-tests.md](../10-10-react-native-app/e2e-api-tests.md) 的 **E2E-009、E2E-010**。
- 规格更新清单见 [implement.md](implement.md) 的「规格与钩子同步清单」。
