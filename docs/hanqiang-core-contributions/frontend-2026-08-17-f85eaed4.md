# refactor(external-integration): split frontend center

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)

## 提交信息

- 仓库：`JSE_UI_AI`
- 完整 SHA：`f85eaed43c539e9779fa7e3c606368777a9dcb5c`
- 父提交：`5f2cd816fab582af0f49196ca9354e336a7c2ad8`
- 作者/提交者：`hanqiang <240448317@qq.com>`
- 时间：`2026-08-17 14:21:17 +0800`
- 原始主题：`refactor(external-integration): split frontend center`
- 变更规模：17 个文件，新增 3,622 行，删除 2,207 行

这次提交把原本约 1,831 行的 `ExternalIntegrationCenter.vue` 页面收敛为约 471 行的编排层；配置表单、回调表单、列表、筛选、详情和 Profile 编辑逻辑移到可独立复用的组件、composable 与纯函数模块。服务、类型、路由和后端 API 契约不在本提交中改变。

## 文件地图（提交时的完整 17 个文件）

| 边界 | 文件 | 可复用职责 |
| --- | --- | --- |
| 页面编排 | `src/pages/ExternalIntegrationCenter.vue` | 持有页面权限、保存动作和弹窗壳；组合子组件与两个 composable |
| 编辑状态 | `src/composables/useExternalIntegrationEditorState.ts` | 配置/回调草稿、Key 轮换、测试、日志和网络尝试详情的状态机 |
| 记录状态 | `src/composables/useExternalIntegrationRecords.ts` | 配置、回调、日志、网络尝试、认证拒绝统计的加载、筛选和分页 |
| 配置表单 | `src/components/externalIntegration/ExternalIntegrationConfigEditorForm.vue` | 系统边界、方向开关、协议/主机/端口/CIDR 白名单和入站 Key |
| 回调表单 | `src/components/externalIntegration/ExternalIntegrationCallbackEditorForm.vue` | 受控 contract、入站固定契约、出站查询条件和 Profile 子编辑器 |
| Profile UI | `src/components/externalIntegration/ExternalIntegrationHttpProfileEditor.vue` | URL、方法、超时、Header、Body、响应映射和脱敏规则的表单 |
| Profile 状态 | `src/components/externalIntegration/useExternalIntegrationHttpProfileEditor.ts` | Profile 读取、校验、合并、预览和 `buildExecutionTemplate()` |
| Profile 编解码 | `src/components/externalIntegration/externalIntegrationHttpProfileCodec.ts` | JSON 工具、变量说明、默认 Body、camelCase/snake_case 兼容和敏感绑定保护 |
| 表单编解码 | `src/components/externalIntegration/externalIntegrationFormCodec.ts` | 文本列表、端口和 JSON 对象的边界解析 |
| UI 契约 | `src/components/externalIntegration/externalIntegrationUi.ts` | Tab、筛选/表单状态、状态选项、标签和列表 Props 类型 |
| 筛选面板 | `src/components/externalIntegration/ExternalIntegrationFilterPanel.vue` | 配置/回调/日志/网络尝试筛选，仅通过事件触发查询或重置 |
| 列表面板 | `src/components/externalIntegration/ExternalIntegrationListPanel.vue` | 四个 Tab、认证拒绝统计、四类表格、操作事件和分页事件 |
| 回调测试 | `src/components/externalIntegration/ExternalIntegrationCallbackTestContent.vue` | 测试设备、上下文 JSON、预览/执行开关和脱敏结果展示 |
| Key 轮换 | `src/components/externalIntegration/ExternalIntegrationKeyRotationContent.vue` | 新 Key 与变更原因输入 |
| 审计详情 | `src/components/externalIntegration/ExternalIntegrationAuditDetailContent.vue` | 脱敏日志事实、配置前后快照、请求/响应/结果摘要 |
| 网络详情 | `src/components/externalIntegration/ExternalIntegrationAttemptDetailContent.vue` | 脱敏目标、HTTP 结果、请求/响应 Header 和 Body |
| 纯函数测试 | `src/components/externalIntegration/__tests__/externalIntegrationHttpProfileCodec.spec.ts` | 验证键名兼容和敏感绑定剥离/恢复 |

## CodeGraph 调用链

```text
ExternalIntegrationCenter
  -> useExternalIntegrationEditorState  (草稿与弹窗状态)
  -> useExternalIntegrationRecords       (集合、筛选、分页)
  -> ExternalIntegrationFilterPanel / ExternalIntegrationListPanel
  -> ConfigEditor / CallbackEditor / KeyRotation / CallbackTest
  -> AuditDetail / AttemptDetail

CallbackEditor
  -> ExternalIntegrationHttpProfileEditor
     -> useExternalIntegrationHttpProfileEditor
        -> externalIntegrationHttpProfileCodec
```

页面仍直接调用已有的 `externalIntegrationService`；本提交没有复制请求逻辑到子组件。CodeGraph 可复核的主要入口如下：

```bash
rtk codegraph explore "ExternalIntegrationCenter useExternalIntegrationEditorState useExternalIntegrationRecords ExternalIntegrationHttpProfileEditor"
rtk codegraph explore "externalIntegrationHttpProfileCodec externalIntegrationFormCodec ExternalIntegrationListPanel"
```

## 可迁移的设计契约

### 1. 页面只做编排和副作用

- 页面统一持有 `configForm`、`callbackForm`、`callbackExecutionTemplate` 和保存中的 `saving` 状态。
- 页面负责权限判断、输入校验、调用 service、错误提示和保存后刷新。
- 子组件不拼接 API URL，不负责 API 请求错误提示；通过 `v-model`、事件和暴露方法回传结果。
- 配置、Key 轮换、回调测试使用 `PmsDialogShell`；日志和网络尝试使用 `JseDrawerShell`，尺寸、关闭保护和 footer 由页面统一配置。

### 2. 两个 composable 各有单一所有权

`useExternalIntegrationEditorState` 管理编辑流程：打开/关闭、草稿重置、乐观锁版本、受保护模板快照、测试结果和详情对象。关闭时清空敏感输入和选择对象，避免旧草稿泄漏到下一次创建。

`useExternalIntegrationRecords` 管理服务端集合：首次加载用 `Promise.all` 并发请求配置、回调、日志、网络尝试和认证拒绝统计；筛选或分页只刷新相关集合；所有 API 异常统一转换为页面可显示的错误。

### 3. 子组件接口保持窄而稳定

| 组件 | 输入 | 输出 |
| --- | --- | --- |
| `ExternalIntegrationConfigEditorForm` | `v-model` 表单、`showInboundKey`、`disabled` | `update:showInboundKey` |
| `ExternalIntegrationCallbackEditorForm` | `v-model` 表单、`executionTemplate`、`configs`、受保护模板、`disabled` | `update:executionTemplate`；暴露 `buildExecutionTemplate()` |
| `ExternalIntegrationFilterPanel` | `filters`、`configs`、`callbacks` | `search`、`reset`、`config-change` |
| `ExternalIntegrationListPanel` | 四类记录、统计、分页和权限 | 编辑/轮换/测试/详情/分页等动作事件 |
| 详情/测试/轮换内容组件 | 对象或可变表单、`disabled` | 仅通过父级表单响应式更新 |

回调类型切换时，入站查询/写入固定 contract 和空 `execution_template`；出站查询才进入 Profile 编辑器，并要求制造类型。表单所属外部系统在编辑已有回调时不可变更。

### 4. Profile 解析和校验集中在 composable

`useExternalIntegrationHttpProfileEditor` 通过 `watch` 将服务端模板拆为可编辑行，构建时再合并回单一对象：

- URL 非空；HTTP 方法仅允许 `GET/POST/PUT/PATCH/DELETE`；超时必须大于 0。
- Header 名称和值必填且不重复，值必须解析为 JSON 字符串；Body 可为空，否则必须是有效 JSON。
- 成功 HTTP 状态码必须是 `100..599` 的整数并去重。
- 出站查询结果映射只能使用登记字段，至少包含 `equipment_code` 和 `mes_state`；响应 Header 掩码名与 Body 掩码路径不能为空或重复。
- 高级兼容 JSON 必须是对象，禁止编辑 `sensitiveBindings`/`sensitive_bindings`；预览先剥离敏感绑定，保存时只从服务端受保护快照恢复。
- `targetUrlTemplate`、`target_url_template`、`target_url` 以及 Profile 内的 camelCase/snake_case 键按原有形状读取和写回，避免迁移时制造第二份字段事实源。

`externalIntegrationFormCodec` 只做边界转换：逗号/换行分隔的文本列表、1–65535 端口和 JSON 对象解析。它不承担业务保存或网络请求。

## 从旧页面迁移的最小步骤

1. 保留原有 service、DTO、路由和权限键；先把页面中的数据请求与编辑状态分别搬到两个 composable。
2. 按“配置/回调表单 → Profile 编辑器 → 筛选/列表 → 详情内容”的顺序提取组件，保持父页面草稿为唯一事实源。
3. 把 JSON、端口、Profile 键兼容和敏感字段处理移到纯函数；组件只消费结构化状态。
4. 让回调表单以 `buildExecutionTemplate()` 作为保存前唯一校验入口，入站回调显式返回 `{}`。
5. 最后统一 Dialog/Drawer 的关闭保护、保存中禁用和 footer；删除旧页面中的重复模板。
6. 若目标项目没有 `PmsDialogShell`，只替换壳组件，不改变子组件的输入/输出契约。

## 验证与回查

提交级回查：

```bash
rtk git -C frontend/JSE_UI_AI show --stat --oneline f85eaed4
rtk git -C frontend/JSE_UI_AI show --name-status --format=fuller f85eaed4
```

最小前端验证：

```bash
rtk npm --prefix frontend/JSE_UI_AI run test -- src/components/externalIntegration/__tests__/externalIntegrationHttpProfileCodec.spec.ts
rtk npm --prefix frontend/JSE_UI_AI run type-check
```

迁移项目应另外补充页面、service 和路由测试，至少覆盖：保存失败不关闭弹窗、乐观锁版本原样传递、敏感绑定不出现在预览、旧键名可读取且不产生重复键、筛选和分页只发出预期请求。

## 历史边界与后续提交

- `f85eaed4` 是前端结构重构，不实现后端认证、幂等、审计或出站网络策略；这些能力由配套后端提交提供。
- 该提交时的 callback 类型只有 `outbound_query`、`inbound_query`、`inbound_write`，没有出站事件路由、场景变量或事件映射编辑器。
- 事件路由和场景变量是后续提交（如 `14d08c36`、`7c6ca57c`、`f75e5a09`、`d7efa7e6`）增加的能力；迁移基础拆分时不要把这些增量误当作本提交的必要依赖。
- 当前工作树可能包含后续对同名组件的增量修改；本文文件地图和契约以 `f85eaed4` 记录的树为准。

## 归档说明

该提交满足总览的公共层筛选规则，按“页面编排—状态管理—受控表单—纯函数 Profile”边界归档。完整文件清单、父提交和验证命令均可由 Git 回查。
