# 审批流可复用实现指南

本文把以下提交中已经验证过的审批能力整理为跨项目蓝图：

- [fb4c0214：OR 并行与回调状态](backend-2026-01-20-fb4c0214.md)
- [f68b3c8d：事件载荷与通知桥接](backend-2026-01-21-f68b3c8d.md)
- [eb5e17b6：角色、监控与弃审检测](backend-2026-01-21-eb5e17b6.md)
- [7c805e02：催办、重建、版本快照与通知基础设施](backend-2026-01-26-7c805e02.md)
- [6cc930bc：资源授权与详情收口](backend-2026-01-30-6cc930bc.md)
- [f315a60f：审批前端功能闭环](frontend-2026-01-26-f315a60f.md)
- [d45da2b5：详情展示与路由收口](frontend-2026-01-30-d45da2b5.md)
- [9dc50a5b：角色/工作流列表聚合统计与可观测性](backend-2026-07-30-9dc50a5b.md)
- [29e83a12：角色/工作流列表单请求与弹窗懒加载](frontend-2026-07-30-29e83a12.md)
- [cdf8843a：工作流详情字段投影、短缓存与 Server-Timing](backend-2026-08-04-cdf8843a.md)
- [82ffe275：前端工作流详情请求合并与强制刷新失效](frontend-2026-08-04-82ffe275.md)

初版领域模型和超时机制见 [审批流初版](backend-2026-01-16-caa33d2a.md) 与 [主流程/超时完善](backend-2026-01-16-c32e1c10.md)。本文只保留可迁移的规则，不要求复制现有项目的目录、框架或业务模块。

## 1. 目标与非目标

### 目标

提供一个可被采购、招聘、质量、资产等业务复用的审批内核，覆盖：工作流配置、角色解析、流程实例、串行/AND/OR 节点、抢单审批、退回/否决/取消/弃审/重提、超时、事件回调、通知、监控和审计。

### 非目标

- 不把具体业务表写入审批内核；通过 `BusinessCode + BusinessData + Module` 或显式适配器桥接。
- 不把企业微信作为唯一通知渠道；通知应走通用事件/消息接口。
- 不把前端按钮状态当作授权；所有资源权限在服务层复核。

## 2. 推荐分层

```text
API / RPC
  -> Application Service
     -> WorkflowService       工作流配置与版本
     -> RoleService            角色成员与动态审批人解析
     -> NodeAssignmentService  当前阶段节点实例化
     -> ProcessService         流程状态、推进、重提、运维
     -> ApprovalService        审批动作、抢单与终态
     -> TimeoutService         超时扫描，复用 ApprovalService/ProcessService
     -> ApprovalEventPayloads  事件数据组装
     -> EventDispatcher        配置匹配、日志、异步执行
     -> Notification Adapter   企微/邮件/站内信等渠道
  Frontend
     -> ApprovalDialog         审批动作与意见输入
     -> Process pages          我的流程/待审批/监控/详情
     -> WorkflowConfig         工作流与节点可视化编辑
     -> API services/types      HTTP 适配与唯一类型源
```

CodeGraph 对当前实现的核心证据是：审批路由调用 `ApprovalService.handle_approval()`，再进入 `ProcessService.advance_process()` 和 `NodeAssignmentService.assign_next_stage()`；所有审批事件最终进入通用 `event_dispatcher.publish()`。迁移时保持这条单向调用链，避免每个业务模块各写一套推进器。

## 3. 最小数据模型

### 3.1 工作流主表

建议字段：

| 字段 | 约定 |
| --- | --- |
| `WorkflowID/Code/Name` | 主键、唯一编码、展示名 |
| `FeatureID/FeatureNodeCode` | 业务功能挂载点，可选 |
| `InitiationMode` | 1 手动、2 半自动、3 自动 |
| `FlowAdminRoleID` | 流程管理员角色，必须是 `RoleType=2` |
| `IsEnabled/IsSystem/IsDeleted` | 生命周期与软删除 |

### 3.2 工作流节点表

| 字段 | 约定 |
| --- | --- |
| `NodeID/WorkflowID` | 节点主键和工作流外键 |
| `NodeLevel` | `stage.order`，如 `1.2`，只允许正整数 |
| `NodePosition` | 1 首、2 中间、3 末、4 唯一 |
| `ParallelPolicy` | 1 串行、2 AND、3 OR |
| `IsSingleApproval` | 1 时覆盖并行策略，强制串行 |
| `RoleID` | 审批人/动态角色 |
| `TimeoutHours/TimeoutAction` | 超时小时数及 `AutoApprove/Ignore` |
| `EnableWXNotify` | 是否启用渠道通知 |

节点配置更新应采用软删除+新版本插入；不要原地覆盖已运行流程使用的节点。

### 3.3 角色表与成员表

`RoleType` 至少支持：

1. 静态审批人角色；
2. 流程管理员角色；
3. 动态部门负责人；
4. 部门审批人列表（逐级）；
5. 发起人自选审批人。

角色成员表保存 `RoleID + UserID + IsDeleted`。动态角色不应伪造成员写入，而应在分配时通过组织适配器解析。

### 3.4 流程实例与节点实例

流程主表关键状态：

| `ProcessStatus` | 含义 |
| --- | --- |
| 1 | 待确认 |
| 2 | 进行中 |
| 3 | 已通过 |
| 4 | 已否决 |
| 5 | 已退回 |
| 6 | 已取消 |
| 7 | 已弃审 |

回调状态独立维护：`CallbackStatus=0 无、1 执行中、2 成功、3 失败`。

节点实例保存：`ProcessNodeID/ProcessID/NodeID/ApproverID/ApproveStatus/NodeLevel/NodePosition/NodeGeneration/ApproveComment/AssignTime/ApproveTime`。节点创建时复制配置快照，审批和推进只使用实例上的 `NodeLevel/NodeGeneration`。

节点状态：`1 未处理、2 同意、3 否决、4 退回、5 失效`。抢单模式下 `ApproverID` 初始为空或全零，审批成功时写入真实操作人。

## 4. 角色解析与节点分配

NodeAssignmentService 建议提供两个稳定接口：

```text
assign_first_stage(process, workflow, generation, applicant, selected_approvers)
assign_next_stage(process, current_level, generation, operator)
```

分配规则：

- 静态角色：查询启用成员，生成一个或多个待办节点；
- 部门负责人：从发起人部门向上查找有效负责人，跳过发起人本人；
- 部门审批人列表：按组织层级和稳定顺序逐级生成同一 `NodeID` 待办；当前级通过后才追加下一级；
- 发起人自选：从 `BusinessData` 读取用户 ID，校验用户存在、启用且未删除；
- AND/OR：同阶段连续且策略相同的节点形成并行组；`IsSingleApproval` 会打断分组。

如果目标项目允许显式并行组，优先新增 `ParallelGroupID`，不要长期依赖“连续节点”启发式。

## 5. 流程推进状态机

`advance_process()` 必须是可复用、可嵌套的事务内函数，禁止内部提交：

```text
读取流程和当前轮次
  -> 读取当前阶段配置（优先流程创建时版本）
  -> 判断串行 / AND / OR 组是否满足推进条件
  -> 失效 OR 组其余待办（如需要）
  -> 分配下一阶段或同节点下一级
  -> 无下一节点则 ProcessStatus=3、写 EndTime
  -> 返回 (process, created_next_nodes)
```

规则：

- 串行：当前节点通过后按数值 `NodeLevel` 分配下一个节点；
- AND：组内所有节点通过后才推进；
- OR：任一节点通过即短路，其他待办置失效；OR 退回应显式拒绝；
- OR 否决：仅当同组没有任何待办时才把流程置为否决；
- 部门审批人列表：同一节点还有下一级时，只追加下一级，不推进阶段；
- 没有下一节点：流程通过并写终态时间。

## 6. 审批动作与并发

`ApprovalService.handle_approval()` 的最小原子步骤：

1. 校验 `ProcessNodeID/OperatorID/Action`；
2. 读取流程、节点、角色、轮次和配置快照；
3. 校验操作人是直接审批人或角色成员；
4. 执行 `UPDATE ... WHERE ApproveStatus=1` 抢单；影响行数为 0 时返回“已处理/已失效”；
5. 按 `APPROVE/RETURN/REJECT` 更新节点和流程状态；
6. 调用不提交事务的 `advance_process()`；
7. 同一事务内写业务终态回调/审计；
8. 提交后发布事件。

人工审批与超时自动审批必须使用相同的锁和条件更新。MySQL `REPEATABLE READ` 下，关键待办查询应使用行锁或重新读取最新状态，避免旧快照重复推进。

## 7. 退回、否决、取消、弃审与重提

- 退回：流程状态 5，允许发起人编辑后局部重提；复制已通过节点，从退回节点继续。
- 否决：流程状态 4，发起人全量重审。
- 取消：流程状态 6，通常由发起人/管理员执行；允许全量重提。
- 弃审：已通过流程状态 7，必须先检测完成回调和弃审回调；若完成回调存在而弃审回调不存在，应阻止操作。
- 弃审重建：在没有活跃 `BusinessCode` 流程时创建新的待确认实例，设置 `ParentProcessID`，复制业务快照并返回新流程 ID。
- 每次重提递增 `NodeGeneration`；历史节点永不与新轮次混用。

## 8. 事件回调与通知

### 8.1 事件清单

推荐统一事件码：

`approval_process_started`、`approval_node_assigned`、`approval_node_approved`、`approval_process_returned`、`approval_process_rejected`、`approval_process_completed`、`approval_process_cancelled`、`approval_process_stopped`、`approval_process_abandon`、`approval_process_resubmitted`。

事件载荷至少包含流程/节点 ID、业务编码、工作流 ID、操作者、状态、时间和追踪 ID。通知模板需要的收件人和前端深链由独立 Payload Builder 查询补齐。

### 8.2 回调匹配

事件配置支持：

- `TransactionType`：事务语义，不填表示通配；
- `TargetObjectType=APPROVAL_FLOW`；
- `TargetObjectID=WorkflowID`：工作流专属配置，空值为全局配置；
- `ScenarioConditions` 与回调级 `TriggerCondition`。

建议采用“专属优先、全局兜底”：专属配置创建了回调日志时，不再执行同事件码的全局配置；专属无匹配日志时才回退全局。

### 8.3 事务边界

主审批事务提交后再派发事件。事件发布异常：

- 不回滚已提交的审批结果；
- `trigger_event()` 回写 `CallbackStatus=3` 并保留错误；
- 通知类 `trigger_notify_event()` 不修改审批主表状态；
- 依靠事件日志、重试和补偿任务恢复。

## 8.4 前端页面与组件契约

前端只负责交互、展示和 API 适配，不能根据状态号自行推断资源权限或执行业务变更。推荐保留以下边界：

- `ApprovalDialog` 接收 `PendingApprovalItem`，统一处理 `APPROVE/RETURN/REJECT`；`RETURN` 必须同时满足权限和 `NodePosition=2/3`，提交函数再次校验。
- `MyProcesses`、`PendingApprovals`、`ProcessMonitoring` 和 `ProcessDetail` 将流程详情与工作流节点配置合并成 `visualStages`，按数值 `NodeLevel` 排序并展示 `ApproveStatus/ApproveComment`。
- 监控页通过 `listProcesses`、`getUrgeMeta`、`urgeProcess`、`checkAbandon`、`abandonProcess` 形成列表、催办和弃审闭环；状态汇总兼容数字键与英文键。
- 详情抽屉保存列表行的 `Can*` 字段作为操作上下文；深链打开没有列表行时，必须补拉可见列表项或隐藏操作按钮。
- `WorkflowNodeConfig` 的拖拽只规范化阶段内 `NodeLevel=stage.order` 和 `ParallelPolicy=1/2/3`；最终校验与版本保护仍在后端。
- 用户编辑页默认不提交密码，只有显式勾选修改密码才发送 `Password`，避免浏览器自动填充造成误更新。

节点展示建议使用统一 UI 模型：

```ts
type VisualWorkflowNode = {
  NodeLevel: string
  NodeName: string
  RoleName: string
  ApproverName?: string | null
  ApproveStatus: number
  ApproveComment?: string | null
  Timestamp?: string
}
```

审批意见在同意、否决、退回等已处理状态显示并保留换行；`ProcessStatus=7` 时显示 `AbandonOperatorName/AbandonTime/AbandonReason`，历史数据缺失字段应安全显示占位符。

## 9. 超时与定时任务

超时扫描建议每 5 分钟运行一次，批量处理：

1. 粗筛 `AssignTime`，再按 `AssignTime + TimeoutHours` 精确判断；
2. 只处理 `ApproveStatus=1` 且流程 `ProcessStatus=2` 的节点；
3. `AutoApprove` 写 SYSTEM 操作者和“超时自动通过”批注；`Ignore` 不改变状态；
4. 使用条件更新和流程行锁避免与人工审批重复；
5. 调用同一个 `advance_process()`，提交后发布节点通过/节点分配/完成事件；
6. 记录批次、处理数、失败数，支持安全重入。

超时粒度为小时，轮询频率只决定延迟，不等于精确触发时刻；验收应允许分钟级误差。

## 10. 监控、催办与审计

### 10.1 监控

监控列表按可见工作流过滤，返回分页数据和不受分页影响的状态摘要。流程详情授权顺序建议为：发起人 → 系统管理员 → 工作流管理员 → 直接审批人/角色成员 → 拒绝。

### 10.2 催办

- 仅进行中流程可催办；系统管理员或流程管理员可操作；
- 选择最早待办，AND/OR 可按当前阶段批量选择；
- 直接审批人优先，角色成员兜底；按 `WXUserID/UserID` 去重；
- 1 小时冷却，接口返回 `LastUrgeTime/NextUrgeTime/CooldownSecondsRemaining`；
- 先写操作日志 `NotifyStatus=1`，发送完成后同步 3=成功/4=失败。

### 10.3 操作日志

操作日志至少覆盖 `ABANDON/URGE/CANCEL/STOP/RESUBMIT`，保存原因、扩展 JSON、通知日志 ID 和错误信息。日志写入失败不应阻塞主流程，但状态变更和审计失败必须告警。

### 10.4 审批配置列表性能与可观测性

角色和工作流配置页是低频管理页面，但经常同时展示分页数据与启用/停用汇总。跨项目复用时固定以下边界：

```text
一次列表请求
  -> 当前页数据
  -> 一次条件聚合（total / filtered_total / enabled / disabled）
  -> 当前页 ID 的 GROUP BY 批量计数
  -> 页面同时更新表格、分页和统计卡片
```

- 后端 `get_list_statistics()` 只执行一条聚合 SQL。外层先应用 `IsDeleted=0`、关键字和角色类型，`is_enabled` 通过 `CASE` 计算 `filtered_total`，因此 `statistics.enabled/disabled` 不会因当前状态筛选变成局部统计。
- 顶层 `total` 等于 `filtered_total`，只用于当前筛选分页；`statistics.total` 是同一关键字/角色类型范围内的全状态总数。空结果必须返回 0，不能由前端当前页估算。
- 当前页角色用户数、工作流节点数使用 `IN + GROUP BY` 批量查询；禁止在逐行渲染或序列化循环中查询详情。
- 前端角色页/工作流页各只调用一次列表 service，直接消费 `res.statistics`。状态切换、删除或保存后重新拉取列表，避免本地行状态与统计卡片分叉。
- 工作流功能模块和流程管理员角色属于低频弹窗选项：首次进入页面不加载，打开新建/编辑弹窗时再加载；使用 loading 与已有数据条件防止重复请求，分页遵守后端上限（当前为 100）。
- 请求级计时只对白名单 `GET /api/approve/roles`、`GET /api/approve/workflows` 开启，阶段固定为 `auth_user`、`auth_roles`、`permission`、`list_query`、`status_summary`、`detail_count`。通过 `Server-Timing` 暴露阶段和 `total`，并在总耗时超过 300ms 时记录 `approval_list_slow_request`（含 request ID、路径、状态码和阶段耗时）。
- `Server-Timing` 是诊断信息，不是业务降级开关；认证/权限仍按原有 401/403 语义执行，未命中白名单的请求不应创建计时上下文。

迁移到其它项目时，只需替换 ORM、HTTP 中间件和权限适配器，保留上述响应字段、查询次数和慢请求字段名即可。

### 10.5 工作流详情读取性能与缓存

工作流列表进入编辑、流程详情页展示节点时，详情接口只需要工作流配置和角色名称，不应加载运行中的流程历史或大字段 JSON。推荐固定为以下查询边界：

```text
GET /approve/workflows/{workflow_id}
  -> 主表字段投影（1 次）
  -> 未删除节点字段投影（1 次）
  -> 去重 RoleID 批量名称查询（1 次，可为空）
  -> DTO 序列化与短 TTL 缓存
```

- 主表和节点表使用显式列投影，过滤 `IsDeleted=0`；不要直接返回带 `selectin`/懒加载关系的 ORM 实体，以免详情读取触发流程主表、节点实例或审批历史 JSON。
- 节点按数值 `(stage, order)` 排序（如 `1.2` 在 `1.10` 前），并将数据库 BIT/bytes 标志转换为稳定布尔值。
- 角色名称使用去重 ID 的单条 `IN` 查询，禁止在节点序列化循环中逐条查询。
- 可在服务实例内提供约 5 秒短缓存，并返回深拷贝，防止调用方修改缓存对象；缓存命中和过期都应可观测。
- 工作流创建、更新、删除成功提交后必须失效对应 `WorkflowID` 的详情缓存。多进程/多副本部署不能依赖本地字典，应改用共享缓存或失效事件。
- 路由可将 `cache/workflow/nodes/roles/serialize/total` 阶段耗时写入 `Server-Timing`；跨域前端需要在 CORS `expose_headers` 中显式暴露该头。

这类缓存只优化短时间重复读取，不改变工作流版本快照：已运行流程仍应通过流程专用查询选择创建时节点版本。`Server-Timing` 是诊断信息，不参与权限、错误或重试决策。

### 10.6 前端工作流详情缓存与请求去重

工作流配置页、流程详情页和节点配置页可能在同一时刻读取同一个工作流。将去重逻辑放在共享 `workflowService`，页面只负责在业务动作后要求强制刷新：

```text
getWorkflowDetail(workflow_id)
  -> token + NUL + workflow_id 缓存键
  -> 未过期缓存：直接返回
  -> 相同键有 pending Promise：复用
  -> 否则发起 GET，成功后缓存 30 秒
```

- 缓存必须按当前 access token 隔离；登出、切换账号或权限上下文变化时清空全部条目。
- `updateWorkflow`、`deleteWorkflow` 成功后按 `WorkflowID` 失效；`ProcessDetail` 在确认、审批成功、取消/中止等 force refresh 前先失效再读取。
- 失效不要求取消已发出的请求，但旧请求完成时必须通过 Promise 身份和 token 检查，不能重新写回已失效或新用户缓存。
- 缓存命中返回的是同一对象还是副本必须写入项目契约；可变调用方应复制，避免修改缓存污染其它页面。
- 该策略只提供单标签页/单运行时短缓存；跨标签页、跨进程或多副本一致性需要共享缓存或失效事件。

前端 30 秒缓存与后端 [`cdf8843a`](backend-2026-08-04-cdf8843a.md) 的 5 秒服务实例缓存可以叠加：前者减少浏览器重复请求，后者减少详情投影查询；两者都不改变 API、权限或审批状态机。

## 11. 跨项目迁移步骤

1. 先建立状态字典、UUID/BIT/JSON 适配层和统一时区；
2. 建表：工作流、节点、角色、角色成员、流程主表、流程节点、操作日志；
3. 迁移 WorkflowService/RoleService/NodeAssignmentService/ProcessService/ApprovalService，先不接业务回调；
4. 为串行、AND、OR、部门角色、抢单、超时补集成测试；
5. 接入事件配置/日志/回调 worker，验证失败补偿；
6. 接入通知渠道和模板深链，再启用催办；
7. 最后迁移监控、弃审重建和权限码，执行数据范围验收；
8. 只复制源代码职责，不复制 `coverage.xml`、环境配置、硬编码业务模块和开发地址。

## 12. 验收清单

- [ ] 单节点串行流程可启动、审批并完成。
- [ ] 多节点串行按数值 `NodeLevel` 顺序推进。
- [ ] AND 组全部通过才推进，OR 组任一通过即短路。
- [ ] OR 退回被拒绝，OR 全部否决才终止流程。
- [ ] 静态角色、部门负责人、部门审批人列表、发起人自选均能分配。
- [ ] 两个用户并发审批同一节点只有一个成功。
- [ ] 超时 AutoApprove 只处理一次，Ignore 不改变状态。
- [ ] 退回/否决/取消/弃审/重提的状态、父子流程和轮次正确。
- [ ] 完成回调存在但弃审回调缺失时阻止弃审。
- [ ] 工作流更新后，旧流程仍读取创建时节点版本。
- [ ] 事件专属配置优先，全局配置只在专属无日志时兜底。
- [ ] 事件失败不回滚主业务，回调状态和日志可追踪、可重试。
- [ ] 监控、详情、催办均按服务层资源权限过滤。
- [ ] 通知日志可同步成功/失败，重复告警不会递归污染日志。
- [ ] 角色/工作流列表单次请求同时返回分页数据和 `statistics`，页面没有额外三次统计请求。
- [ ] 状态筛选下 `statistics.enabled/disabled` 仍是全局（关键字/角色类型范围）统计，顶层 `total` 与筛选结果一致。
- [ ] 当前页成员数/节点数通过批量 `GROUP BY` 获取，无逐行 N+1 查询。
- [ ] 工作流低频选项仅在弹窗打开时加载，分页请求遵守 100 的上限或目标项目等价限制。
- [ ] 审批列表响应可读取 `Server-Timing` 阶段；超过阈值的慢请求能按 request ID 和阶段耗时定位。
- [ ] 工作流详情只执行主表、节点、角色投影查询，不触发流程历史关系或大字段 JSON 加载。
- [ ] 工作流详情节点按数值 `NodeLevel` 排序，角色名称通过批量查询返回，无逐节点 N+1。
- [ ] 详情短缓存命中返回独立对象；创建/更新/删除提交后对应缓存立即失效，多实例部署使用共享失效机制。
- [ ] 工作流详情响应包含固定阶段的 `Server-Timing`，CORS 暴露头配置后浏览器可读取，且不改变认证/404 语义。
- [ ] 同一 token/workflow 的并发详情请求只发送一次，后续短时间读取命中缓存。
- [ ] `updateWorkflow`、`deleteWorkflow` 和详情页 force refresh 后会重新获取工作流详情。
- [ ] token 变化不会复用旧用户缓存；被失效的旧 pending 请求不能重新写回缓存。

## 13. 复核入口

```bash
rtk codegraph explore "ApprovalService.handle_approval ProcessService.advance_process NodeAssignmentService.assign_next_stage"
rtk codegraph explore "build_node_assigned_event_payloads trigger_event ProcessService.urge_process get_by_workflow_for_process"
rtk codegraph explore "CRUDRole.get_list_statistics CRUDWorkflow.get_list_statistics RoleService.list_roles WorkflowService.list_workflows"
rtk codegraph explore "begin_approval_list_timing measure_approval_list_phase HttpObservabilityMiddleware.__call__"
rtk codegraph explore "WorkflowService.get_workflow_detail get_workflow_detail workflow detail optimize"
rtk codegraph explore "WorkflowService invalidate_workflow_detail_cache create_workflow update_workflow delete_workflow get_workflow_detail"
rtk codegraph explore "getWorkflowDetail invalidateWorkflowDetailCache ProcessDetail.loadPage workflowDetailPending"
rtk codegraph explore "RoleManagement WorkflowConfig ApprovalListStatistics loadWorkflowDialogOptions"
rtk git -C backend/JSECommon log --oneline -- app/services/approve
rtk git -C backend/JSECommon show --name-status --format=fuller fb4c0214
rtk git -C backend/JSECommon show --name-status --format=fuller f68b3c8d
rtk git -C backend/JSECommon show --name-status --format=fuller eb5e17b6
rtk git -C backend/JSECommon show --name-status --format=fuller 7c805e02
rtk git -C backend/JSECommon show --name-status --format=fuller 6cc930bc
rtk git -C backend/JSECommon show --name-status --format=fuller 9dc50a5b
rtk git -C frontend/JSE_UI_AI show --name-status --format=fuller 29e83a12
rtk git -C backend/JSECommon show --name-status --format=fuller cdf8843a
rtk git -C frontend/JSE_UI_AI show --name-status --format=fuller 82ffe275
```
