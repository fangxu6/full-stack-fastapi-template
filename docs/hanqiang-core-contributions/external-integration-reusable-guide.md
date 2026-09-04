# 外部集成中心可复用实现指南

本文把外部系统配置、固定入站契约、出站查询和 FT 出站事件整理成可迁移的实现边界。结论来自以下提交；前五个提供中心拆分、对话框和后端 facade，后五个组成事件路由增量链：

- [4c6d6b52：前端外部集成中心](frontend-2026-08-14-4c6d6b52.md)
- [e09e795b：前端编辑器与对话框统一](frontend-2026-08-14-e09e795b.md)
- [f85eaed4：前端中心拆分与状态边界](frontend-2026-08-17-f85eaed4.md)
- [9111e45b：后端固定契约与审计中心](backend-2026-08-14-9111e45b.md)
- [a4193e5e：后端服务职责拆分](backend-2026-08-17-a4193e5e.md)
- [14d08c36：FT 出站事件路由编辑器](frontend-2026-08-25-14d08c36.md)
- [7c6ca57c：按场景展示回调变量](frontend-2026-08-26-7c6ca57c.md)
- [f75e5a09：FT 设备主数据事件](frontend-2026-08-27-f75e5a09.md)
- [d7efa7e6：回调条件字段编辑器](frontend-2026-08-27-d7efa7e6.md)
- [da7f708f：回调条件运算符与区域事实](backend-2026-08-27-da7f708f.md)

## 1. 目标与边界

外部集成中心同时服务管理面和运行面：管理人员配置外部系统、回调 Profile、Key、预览/测试并查看审计；运行面接收固定入站请求、执行受控出站查询，或把 PMS 事件投递到外部系统。

不要把它实现成任意 URL 代理、脚本执行器、SQL 网关或目标表写入器。目标系统差异必须落在白名单 Profile、固定 contract、设备事实映射和事件适配器中。

## 2. 推荐分层与数据流

```text
管理 UI
  -> 页面编排 + composable
  -> typed API service
  -> 管理路由/权限
  -> Config/Callback/Profile/Log/Attempt 持久化

PMS 领域事件
  -> 事件事实查询（设备/类型/型号/区域/快照）
  -> 场景与 contract 路由匹配
  -> match_condition（设备事实）
  -> Profile 模板渲染 + eventMappings
  -> pending 投递日志/网络尝试
  -> 脱敏审计与投递租期

固定入站入口
  -> Key/CIDR 认证
  -> 固定 contract/callback
  -> 严格 JSON + 幂等租期
  -> 设备适配器/业务写入
  -> 固定响应信封
```

后端可保留稳定 `ExternalIntegrationService` facade，再组合 `common/shared/management/inbound/outbound/preview/policy` 职责。Mixin 不反向依赖 facade；前端页面不拼接 API URL，所有请求通过一个 service。

## 3. 固定配置和回调契约

| 区域 | 建议字段/约束 |
| --- | --- |
| 配置 | system code/name、owner service、协议/主机/端口/CIDR 白名单、入站 Key、入站/出站开关、状态、版本 |
| 回调 | contract code、callback type、场景、制造类型、match condition、execution template、版本 |
| 入站查询 | `lookup_field` 只允许 `equipment_code/asset_code/serial_number`，另加 `lookup_value` |
| 入站写入 | `items` 每项只含 `equipment_code + mes_state`，最多 200 项 |
| 出站查询 | `outbound_query` + `query` 场景；Profile 结果映射至少含 `equipment_code`、`mes_state` |
| 出站事件 | `outbound_event`；制造类型固定为 `FT`；场景与 contract 必须来自白名单；响应结果映射可为空 |
| 统一响应 | `code`、`message`、`trace_id`；错误分类可检索 |

入站请求体建议限制 64 KiB；严格 JSON 拒绝非 UTF-8、重复对象键和 `NaN/Infinity`。所有输入 schema 在边界处去除必填文本空白并限制长度。

## 4. FT 事件场景、变量和映射

### 4.1 场景白名单

| 场景 | contract | 对外数据范围 |
| --- | --- | --- |
| `ft_equipment_status_non_tester` | `pms.equipment-status.changed.v1` | 状态前后值、设备主数据、更新来源 |
| `ft_equipment_status_tester` | `pms.equipment-status.changed.v1` | Tester 状态前后值、设备主数据、更新来源 |
| `ft_equipment_binding_changed` | `pms.equipment-binding.changed.v1` | 绑定 ID/变更类型/来源、TesterStatus、Before/AfterBinding 路径 |
| `ft_equipment_created` | `pms.equipment.created.v1` | 设备编号、大类、名称、区域、型号、序列号、排产/车规标志、FT 工序、归类、Handler 状态 |
| `ft_equipment_updated` | `pms.equipment.updated.v1` | 与设备新增相同 |
| `ft_equipment_scrapped` | `pms.equipment.scrapped.v1` | 仅设备编号 |

后端必须同时校验：事件回调归属 PMS 服务、制造类型为 `FT`、场景与 contract 一一匹配。前端下拉目录只是辅助，不能替代后端校验。

### 4.2 模板变量

所有状态/绑定事件可使用事件信封变量：

`EventID`、`EventTime`、`EventType`、`EventVersion`、`EventPayload`、`EventData`、`LogID`、`TraceID`、`IdempotencyKey`。

设备新增/编辑在此基础上增加：

`EquipmentCode`、`EquipmentCategory`、`EquipmentName`、`AreaName`、`EquipmentModel`、`SerialNumber`、`CanSchedule`、`IsAutomotive`、`FTProcesses`、`ManufactureTypeCode`、`HandlerStatus`。

绑定事件增加 `FTBindingID`、`ChangeType`、`SourceType`、`SourceID`、`TesterStatus` 及 `$.EventData.BeforeBinding/AfterBinding` 下的主/子设备编码和型号路径变量。报废场景只公开 `${EquipmentCode}`；不要用通用变量列表覆盖这个最小数据集。

变量帮助应由 `getTemplateVariableGuides(eventScenario)` 这类纯函数按场景返回，并与后端 `EVENT_TEMPLATE_VARIABLES` 集合校对。默认 Body 示例只是起步模板，不是目标系统协议。

### 4.3 事件字段映射

`eventMappings` 结构为“事件字段 -> PMS 源值 -> 外部目标值”，只改变外部报文，不改变 PMS 状态或绑定事实。字段白名单按 contract 分开：

| contract | 允许字段摘要 |
| --- | --- |
| 状态变更 | `ManufactureTypeCode`、设备标识/类型、资产编码、序列号、旧/新主状态、旧/新明细状态、旧/新状态桶、更新来源及 ID |
| 绑定变更 | `ManufactureTypeCode`、`ChangeType`、`FTBindingID`、`SourceType`、`SourceID`、`TesterStatus` |
| 设备新增/编辑 | `EquipmentCode`、`EquipmentCategory`、`EquipmentName`、`AreaName`、`EquipmentModel`、`SerialNumber`、`CanSchedule`、`IsAutomotive`、`FTProcesses`、`ManufactureTypeCode`、`HandlerStatus` |
| 设备报废 | `EquipmentCode` |

建议限制最多 20 个字段、每字段最多 100 个源值，源值/目标值 trim 后长度不超过 255；保存统一写 `eventMappings` 并删除 `event_mappings` 别名。场景切换必须清除旧映射。

## 5. 条件契约：前后端同一套运算符

### 5.1 字段与运算符

路由条件只针对设备事实：

```text
equipment_code        -> EquipmentCode
equipment_name        -> EquipmentName
asset_code            -> AssetCode
serial_number         -> SerialNumber
manufacture_type_code -> ManufactureTypeCode
equipment_type_code   -> EquipmentTypeCode
equipment_type_name   -> TypeName
```

支持 `$eq`、`$ne`、`$gt`、`$gte`、`$lt`、`$lte`、`$in`、`$nin`、`$exists`。多个字段按 AND 关系求值。

```json
{
  "equipment_code": {"$in": ["FT-A", "FT-B"]},
  "equipment_type_code": {"$nin": ["FT-Scrap"]},
  "equipment_type_name": {"$exists": true}
}
```

### 5.2 兼容和边界

- 后端保存时把历史标量归一为 `$eq`、历史数组归一为 `$in`；空条件写成 `None`，表示不限设备。
- 对象表达式必须只有一个运算符；`$in/$nin` 只能接收标量数组；`$exists` 只能接收布尔值；未知字段、运算符和非法值直接拒绝并记录配置审计。
- 共享 `condition_evaluator` 负责所有比较，支持点号路径；`$in/$nin` 对数组实际值按任一元素命中；比较异常返回 false。
- 当前 `$exists` 用“实际值不是 `None`”判断，缺失和明确 null 不区分。目标项目若需区分，先扩展共享评估器和测试。
- 前端 `ConditionEditor` 用 `fieldOptions`、`disabled`、`testIdPrefix` 接入受控字段目录，同时保留 JSON 模式。非法 JSON 保留原文本并显示错误，不能静默丢值。
- 可视化模式尝试把比较值转成有限数字，把 `$exists` 输入 `true/1/是` 转成 true；最终类型校验仍以服务端为准。

## 6. 安全、版本和可观察性

- 入站先验证 Key、配置 active、方向开关和来源 CIDR，再解析固定 callback；认证拒绝、配置不可用和契约错误都写审计。
- 以规范化 JSON 哈希实现 `Idempotency-Key`：相同 Key 不同 payload 返回冲突；处理中返回 409；60 秒租期过期后在行锁内收敛 processing 记录。
- 配置/回调写入使用 `expected_version` 乐观锁；Key 轮换/退休立即使旧 Key 失效，并保存脱敏前后快照。
- URL、Header、Body、响应和错误均结构化脱敏；日志和网络尝试关联 TraceID，禁止记录明文 Key 或 Authorization。
- 事件日志同时保存原始事件报文、映射命中/未命中摘要、事件 ID/场景和投递租期；入站日志继续使用处理租期。
- 主数据/状态事件的 TraceID 应包含稳定业务键（设备编码）与事件 ID，便于跨系统检索。
- 管理配置和测试请求禁用网络层自动重试；生产投递由事件/任务执行器负责，浏览器测试不是投递器。

## 7. 前端复用边界

`ExternalIntegrationCenter` 统一持有草稿、权限、版本和保存副作用；`useExternalIntegrationEditorState` 管理编辑状态，`useExternalIntegrationRecords` 管理集合/筛选/分页。子组件只通过 `v-model`、事件和暴露方法更新。

```text
ExternalIntegrationCenter.vue
  ├─ useExternalIntegrationEditorState.ts
  ├─ useExternalIntegrationRecords.ts
  ├─ ConfigEditor / CallbackEditor
  ├─ FilterPanel / ListPanel
  └─ AuditDetail / AttemptDetail

CallbackEditor
  ├─ ConditionEditor（match_condition）
  └─ HttpProfileEditor
       └─ useExternalIntegrationHttpProfileEditor + *Codec
```

Profile 编辑器的保存入口必须是 `buildExecutionTemplate()`；入站回调显式返回 `{}`，出站查询/事件才校验 URL、方法、超时、Header、Body、响应和事件映射。高级 JSON 禁止编辑敏感绑定，预览永远去敏；旧 camelCase/snake_case 只在读取时兼容，写回单一规范键。

`ConditionEditor` 是可选字段目录的通用组件：已有事件配置页面不传 `fieldOptions` 时仍可自由输入，外部集成传入设备事实目录即可复用。页面不应复制条件解析或运算符列表。

## 8. 后端拆分边界

先保留原有 facade 和 singleton import，再按职责拆分：

- `common`：契约常量、错误信封、严格 JSON、时间和脱敏。
- `management/policy`：配置/回调版本、Key、contract、Profile、条件和事件映射边界。
- `event`：从设备/类型/型号/区域/快照构造权威事件事实，写入 pending 日志。
- `inbound/outbound`：固定入站适配器、出站 Profile 渲染、网络尝试和租期推进。
- `condition_evaluator`：唯一条件比较实现；查询和事件路由都调用它。

测试按 common、management、inbound、outbound、event、profile 和 route 分组；路由测试必须验证权限、错误信封、公开路径、幂等和脱敏。

## 9. 跨项目迁移顺序

1. 先迁移配置/回调 DTO、版本和固定 contract，保留旧 service import 路径。
2. 迁移页面编排、两个 composable、Profile codec 和 Dialog Shell，确保页面草稿是唯一事实源。
3. 增加 `outbound_event` 与场景白名单，再接入变量目录和按 contract 的事件映射。
4. 将 `ConditionEditor` 接入回调表单；前端字段目录与后端设备事实映射保持同名。
5. 在后端保存入口归一化条件、事件映射和空值；所有执行路径改用共享 `condition_evaluator`。
6. 迁移设备事件事实查询和投递日志；新增/编辑可包含区域，报废只输出设备编号；TraceID 使用设备编码。
7. 最后补齐审计/尝试详情和跨层测试，再启用生产投递。逻辑上应先让后端接受新契约，再开放前端保存；`d7efa7e6` 与 `da7f708f` 应作为同一条件能力链验证。

## 10. 最小验收矩阵

| 能力 | 必测断言 |
| --- | --- |
| 配置与版本 | CRUD、Key 轮换/退休、版本冲突返回 409、审计快照脱敏 |
| 入站 | Key/CIDR、严格 JSON、64 KiB/200 项上限、幂等冲突与租期、固定响应信封 |
| 出站查询 | URL/主机白名单、结果映射必填、网络错误可追踪、敏感绑定不回显 |
| 出站事件 | 六场景 contract 一致、FT 制造类型、变量目录隔离、映射命中/未命中、投递租期 |
| 条件 | 九个运算符、标量/数组兼容、字段白名单、非法输入拒绝、多个字段 AND |
| 主数据 | 新增/编辑含 `AreaName`，报废仅 `EquipmentCode`，TraceID 含设备编码 |
| 前端交互 | JSON/可视化双向同步、非法 JSON 不丢失、切换场景/类型清除旧条件和映射、保存中不可关闭 |

推荐回归命令：

```bash
rtk npm --prefix frontend/JSE_UI_AI run test -- src/components/event/__tests__/ConditionEditor.test.ts src/components/externalIntegration/__tests__/ExternalIntegrationAuditDetailContent.spec.ts src/components/externalIntegration/__tests__/ExternalIntegrationHttpProfileEditor.spec.ts src/pages/__tests__/ExternalIntegrationCenter.spec.ts
rtk npm --prefix frontend/JSE_UI_AI run type-check
rtk python3 -m pytest backend/JSECommon/tests/services/test_external_integration_event.py backend/JSECommon/tests/services/test_external_integration_management.py backend/JSECommon/tests/services/test_external_integration_profile.py
```

## 11. 不复制的内容与历史边界

- 不复制具体数据库方言、项目目录、设备表 SQL、开发地址、明文密钥或测试夹具；只迁移职责、字段契约、错误分类、审计约束和边界测试。
- `14d08c36` 只提供三个 FT 事件场景；`7c6ca57c` 提供场景变量；`f75e5a09` 提供设备主数据场景；`d7efa7e6` 提供前端条件编辑和 AreaName UI；`da7f708f` 提供后端归一化、共享求值和 AreaName 事实。
- `f85eaed4` 的页面拆分是基础结构，不要求事件能力；事件目录应作为增量迁移，避免把业务事件硬编码成所有项目的必选依赖。
- 入站 `pending/processing`、幂等租期和网络重试语义属于既有后端能力；不要因为新增事件 Profile 而复用入站处理租期或自动重试。

## 12. CodeGraph 与 Git 复核入口

```bash
rtk codegraph explore "ExternalIntegrationCenter ExternalIntegrationCallbackEditorForm ExternalIntegrationHttpProfileEditor ConditionEditor"
rtk codegraph explore "EVENT_SCENARIO_OPTIONS EVENT_MAPPING_FIELDS_BY_CONTRACT EVENT_MATCH_CONDITION_FIELDS_BY_SCENARIO"
rtk codegraph explore "ExternalIntegrationManagementMixin _normalize_match_condition _match_outbound_condition condition_evaluator"
rtk codegraph explore "ExternalIntegrationEventService _enrich_equipment_context build_equipment_master_event_payload"
rtk git -C frontend/JSE_UI_AI show --stat --oneline 14d08c36 7c6ca57c f75e5a09 d7efa7e6
rtk git -C backend/JSECommon show --stat --oneline da7f708f
```
