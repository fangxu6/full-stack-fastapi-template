# feat(integration): configure callback condition fields

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)

## 提交信息

- 仓库：`JSE_UI_AI`
- 完整 SHA：`d7efa7e6df27d8887d278ac3e736749233ce8a93`
- 父提交：`7336fc77aa052608635fb508c2715f0c7162abdd`
- 作者/提交者：`hanqiang <240448317@qq.com>`
- 时间：`2026-08-27 17:15:02 +0800`
- 原始主题：`feat(integration): configure callback condition fields`
- 变更规模：9 个文件，新增 235 行，删除 33 行

本提交把外部集成回调的“场景条件 JSON”升级为可视化/JSON 双模式编辑器。条件字段来自设备主数据白名单，运算符和值在前端做可逆转换；事件场景切换会同时清除旧条件和旧事件映射，避免跨 contract 污染。

## 文件地图（提交时的完整 9 个文件）

| 边界 | 文件 | 可复用职责 |
| --- | --- | --- |
| 通用条件组件 | `src/components/event/ConditionEditor.vue` | 双模式条件编辑、运算符目录、标量/数组/数字/布尔转换、JSON 错误保留和稳定比较 |
| 条件组件测试 | `src/components/event/__tests__/ConditionEditor.test.ts` | 验证受控字段目录和 `$in` 数组输出 |
| 回调表单 | `src/components/externalIntegration/ExternalIntegrationCallbackEditorForm.vue` | 通过 computed `v-model` 接入 ConditionEditor；场景切换清除条件/映射 |
| Profile UI | `src/components/externalIntegration/ExternalIntegrationHttpProfileEditor.vue` | 移除重复的通用指南面板；为新增/编辑场景显示 `AreaName` 语义提示 |
| Profile 编解码 | `src/components/externalIntegration/externalIntegrationHttpProfileCodec.ts` | 主数据变量增加 `AreaName`，新增/编辑默认 Body 示例包含区域名称 |
| UI 契约 | `src/components/externalIntegration/externalIntegrationUi.ts` | 设备事实条件字段目录、场景索引、主数据事件的 `AreaName` 映射字段 |
| Profile 状态 | `src/components/externalIntegration/useExternalIntegrationHttpProfileEditor.ts` | 删除已无渲染方的 `ExecutionTemplate` 指南对象，保留 Profile 校验/预览 |
| Profile 测试 | `src/components/externalIntegration/__tests__/ExternalIntegrationHttpProfileEditor.spec.ts` | 验证 AreaName 变量/提示及报废场景不显示 |
| 页面测试 | `src/pages/__tests__/ExternalIntegrationCenter.spec.ts` | 验证事件条件字段、运算符和场景/类型切换清理 |

## CodeGraph 调用链

```text
ExternalIntegrationCenter
  -> ExternalIntegrationCallbackEditorForm
     -> getExternalIntegrationMatchConditionFields(callbackType, scenario)
     -> ConditionEditor(v-model="matchCondition", fieldOptions)
        -> rows <-> JSON 文本（watch + applyJson）
     -> ExternalIntegrationHttpProfileEditor
```

复核命令：

```bash
rtk codegraph explore "ConditionEditor ExternalIntegrationCallbackEditorForm getExternalIntegrationMatchConditionFields"
rtk codegraph explore "ExternalIntegrationHttpProfileEditor useExternalIntegrationHttpProfileEditor EVENT_MATCH_CONDITION_FIELDS_BY_SCENARIO"
rtk git -C frontend/JSE_UI_AI show --name-status --format=fuller d7efa7e6df27d8887d278ac3e736749233ce8a93
```

## 条件编辑契约

### 字段目录

所有出站查询和六个 FT 出站事件场景共用设备事实字段目录（JSON 键 -> 设备事实来源）：

| JSON 字段 | 设备事实 |
| --- | --- |
| `equipment_code` | `EquipmentCode` |
| `equipment_name` | `EquipmentName` |
| `asset_code` | `AssetCode` |
| `serial_number` | `SerialNumber` |
| `manufacture_type_code` | `ManufactureTypeCode` |
| `equipment_type_code` | `EquipmentTypeCode` |
| `equipment_type_name` | `TypeName` |

条件只筛选设备事实，不直接筛选事件 Body；这样查询路由和事件路由可以共用匹配器，事件字段映射仍留在 Profile。

### 运算符与双向转换

支持 `$eq`、`$ne`、`$gt`、`$gte`、`$lt`、`$lte`、`$in`、`$nin`、`$exists`。

- 旧的标量表达式读取为 `$eq`，旧的数组读取为 `$in`；未知运算符读取时归一为 `$eq` 但后端保存仍必须拒绝未知运算符。
- `$in/$nin` 的输入按 JSON 解析数组；解析失败保留原始字符串，不能静默丢值。
- 比较运算符尝试转换为有限数字；无法转换时保留文本。
- `$exists` 将 `true/1/是` 视为 true，其余输入为 false。
- JSON 模式失焦时只接受对象；非法 JSON 保留编辑文本并显示错误，不覆盖最近一次有效模型。
- `stableValue` 对字段和嵌套对象排序，避免 JSON 键顺序差异触发 watch 循环或重复 emit。

组件通过 `fieldOptions`、`disabled`、`testIdPrefix` 接收目录和外部状态；没有目录时保留自由文本输入，便于复用到通用事件配置页面。

## 场景切换与 AreaName 边界

- 回调表单的 `matchCondition` 是对 `match_condition_text` 的 computed 适配器，保存时仍由页面拿到结构化对象。
- 事件场景变化会清空 `match_condition_text` 和 Profile 的 `eventMappings`/`event_mappings`，防止旧字段继续匹配新场景。
- `AreaName` 仅属于设备新增/编辑变量与映射；提示语义为 `Equipment.AreaCode` 对应的 `Common_Area.AreaName`。
- 报废场景仍只暴露 `EquipmentCode`，不会因为共享主数据目录而显示 `AreaName`。
- 移除 `ExecutionTemplateGuidePanel` 后，Profile 只保留保存前预览；变量目录仍由场景化表格提供。

## 跨项目迁移步骤

1. 把条件字段目录定义为 `value + label + source` 的纯数据，并按回调类型/场景返回只读数组。
2. 在通用 ConditionEditor 中保留可视化与 JSON 两个入口，使用一个内部行模型和一个归一化比较函数同步，避免双向 watch 回路。
3. 明确旧数据兼容规则（标量 `$eq`、数组 `$in`），但让后端成为最终运算符和类型校验边界。
4. 在场景切换处理器中同时清理条件文本、事件映射和依赖 contract 的临时字段。
5. 将区域等新主数据字段同时加入变量目录、映射目录、默认 Body 提示和后端事件事实查询；删除场景只保留最小字段。
6. 复用到其他 ConditionEditor 调用方时，不改变其 `v-model` 事件名；仅新增可选 props，确保旧页面继续工作。

## 测试与验收

```bash
rtk npm --prefix frontend/JSE_UI_AI run test -- src/components/event/__tests__/ConditionEditor.test.ts src/components/externalIntegration/__tests__/ExternalIntegrationHttpProfileEditor.spec.ts src/pages/__tests__/ExternalIntegrationCenter.spec.ts
rtk npm --prefix frontend/JSE_UI_AI run type-check
```

至少验收：字段下拉只显示登记设备事实；`$in` 数组和 `$exists` 布尔值双向可编辑；非法 JSON 不丢文本；事件场景/类型切换后保存载荷不含旧条件或旧映射；报废场景不显示 `AreaName`。

## 历史边界

- `ConditionEditor` 也被 `EventConfigManagement`、`CallbackConfigManagement` 使用；本提交新增 props 必须保持默认值，不能破坏这些调用方。
- 前端条件编辑需要后端 `da7f708f` 的运算符归一化和共享求值器配套；单独发布前端会导致契约不一致。
- 设备主数据场景和变量目录来自 `f75e5a09`；本提交只补充 AreaName 与条件编辑，不新增事件 contract。

## 归档说明

该提交按“可视化条件编辑器—设备事实字段目录—场景切换清理”边界归档，是把自由 JSON 条件迁移为受控配置的最小实现。
