# 统一状态迁移规则方案

## 文档用途

本文档是项目统一状态迁移规则的方案说明，也是 scheduler、库存纠错、Email Outbox 和库存日报投递现有状态迁移矩阵的唯一规范载体。矩阵以当前代码行为为事实来源，不代表本任务要重构运行时代码。

## 结论摘要

当前项目已经存在多套领域生命周期，但没有统一的状态机引擎。推荐采用方案一：

> 统一状态迁移的描述、并发控制、幂等、审计和测试契约；保留每个领域自己的状态和事件，不建设全局状态矩阵或通用工作流运行时。

方案一统一的是迁移契约，不是所有领域的状态值。调度运行、库存纠错、邮件投递和日报投递的相同词汇可能有不同含义，必须继续由所属领域解释。

## 1. enum、状态与状态矩阵

三者是不同层次：

| 概念 | 职责 | 示例 |
| --- | --- | --- |
| `enum` | 定义字段允许出现的封闭值集合；当前值不决定后续流程时，使用枚举即可。 | `EmailOutboxKind`、`SchedulerRunTrigger` |
| 状态枚举 | 用枚举表示聚合的生命周期阶段，并作为模型、Schema 和持久化值契约。 | `EmailOutboxStatus`、`SchedulerRunStatus` |
| 状态迁移矩阵 | 定义 `当前状态 + 事件 -> 目标状态`，并说明前置条件、副作用、幂等和并发语义。 | `LEASED + DELIVER_SUCCESS -> DELIVERED` |

判断规则：

- 类别、来源、策略、角色和错误分类等只描述“是什么”，使用 `enum`，不要求矩阵。
- 如果当前值会限制下一步、表示终态，或涉及审批、租约、重试、恢复、权限、跨实体副作用或并发控制，则它是工作流状态，应使用状态枚举并在 DDD 设计文档中提供矩阵。
- 简单的状态字段若没有多步流程、恢复/重试、并发边界或跨实体协调，可以只保留状态枚举和领域方法；一旦演化为工作流状态，必须在同一设计变更中补充矩阵。
- 矩阵不替代枚举。新状态优先使用 `<Aggregate>State`，现有语义准确的 `<Aggregate>Status` 不要求改名；事件优先使用 `<Aggregate>Event`，事件值使用 `APPROVE`、`CLAIM`、`DELIVER` 等领域动词。

矩阵中的事件是统一的设计词汇，不意味着当前代码必须已经存在同名事件枚举。复杂领域可以继续通过领域服务命令实现迁移；只有矩阵确实作为代码校验来源时，才在领域模块内定义 `<AGGREGATE>_TRANSITIONS`。

## 2. 当前项目的生命周期盘点

### 2.1 scheduler

`SchedulerRunStatus` 定义在 `backend/app/models/scheduler.py:26-32`，持久化生命周期集中在 `backend/app/modules/scheduler/run_lifecycle.py`：

- `create_run()` 创建排队运行，也记录配置无效和活动运行重叠等预执行终态。
- `claim_dispatchable_runs()` 管理队列投递租约，`release_dispatch()` 处理投递失败后的下一次扫描。
- `claim_execution()` 在行锁下领取 `QUEUED` 或已过期 `RUNNING`，设置执行租约。
- `finish_outcome()` 统一写入 `SUCCEEDED`、`SKIPPED`、`FAILED` 并清理租约。
- `cancel_queued_runs()` 只取消 `QUEUED` 运行；`cleanup_runs()` 清理已完成且超过保留期的记录。

实现位置和职责也记录在 `docs/adr/0012-concentrate-scheduler-run-lifecycle-state.md`。`async-task-guidelines.md` 中陈旧的 `finish_run(...)` 描述由活跃任务 `08-07-correct-scheduler-lifecycle-spec` 负责，本方案不修改该文件。

### 2.2 库存纠错

库存纠错不是单表状态机。申请、WorkItem 和 Attempt 分别维护状态：

- Request：`PENDING_REVIEW`、`APPROVED`、`REJECTED`、`WITHDRAWN`、`STALE`、`APPLIED`、`APPLICATION_FAILED`。
- WorkItem：`APPROVED_PENDING_APPLY`、`RUNNING`、`SUCCEEDED`、`TERMINAL_FAILED`。
- Attempt：`PENDING`、`RUNNING`、`SUCCEEDED`、`TERMINAL_FAILED`。

主要代码边界是 `backend/app/modules/inventory/correction_service.py` 和 `backend/app/modules/inventory/correction_attempts.py`。审批会原子创建 WorkItem 和初始 Attempt；领取会同时更新 WorkItem 与 Attempt；执行结果会联动 Request、WorkItem、Attempt 及库存/审计写入；恢复会创建下一序号 Attempt。不能用一个跨领域矩阵压缩这三条轨迹。

### 2.3 Email Outbox

`EmailOutboxKind` 是邮件类别；`EmailOutboxStatus` 是可靠投递生命周期。实现位于 `backend/app/services/email_outbox.py`：

- `PENDING` 和 `RETRY_WAIT` 只在到期且未超尝试次数时领取。
- `LEASED` 带有过期时间，成功以相同 lease token 完成。
- 投递失败或租约过期根据尝试次数进入 `RETRY_WAIT` 或 `FAILED`。
- 已成功、已失败或 lease token 不匹配的重复结果无副作用。

库存日报继续使用独立的 delivery 表，不并入 Email Outbox。

### 2.4 库存日报投递

日报有两个独立但联动的生命周期：

- Report 负责业务日期快照、收件人解析重试和全部 delivery 的聚合摘要。
- Delivery 负责单收件人的领取租约、SMTP 调用、结果落库和有限重试。

实现位于 `backend/app/modules/inventory/daily_report.py`。日报创建受上海时间 08:00 至 08:15 窗口和 `(processing_unit_id, business_date)` 唯一约束保护；投递使用短事务领取、事务外 SMTP、短事务结果落库。

## 3. 统一方案：领域独立状态 + 共享最小机制

统一迁移契约为：

```text
当前状态 + 领域事件 -> 目标状态
```

所有符合触发条件的 DDD 工作流设计都必须说明：

1. 合法和非法迁移。
2. 业务前置条件和权限边界。
3. 事务所有者及跨表副作用。
4. 行锁、乐观版本或租约校验。
5. 重试、恢复、终态和重复调用语义。
6. 审计和日志记录边界。
7. 合法边、非法边、终态、恢复/重试、幂等和并发测试。

领域必须继续拥有状态枚举、事件/命令、矩阵、业务前置条件、跨表副作用和恢复语义。共享规则不能变成跨领域注册中心，也不能动态执行任意领域回调。

## 状态迁移矩阵（State Transition Matrix）

以下七张矩阵均使用固定列：`当前状态`、`事件`、`目标状态`、`前置条件`、`副作用`、`幂等/并发语义`。`(新建)` 表示对象首次持久化，`不变/拒绝` 用于表达重复调用或非法迁移，不是新的状态值。

### scheduler.scheduler_run 状态迁移矩阵

来源：`backend/app/models/scheduler.py`、`backend/app/modules/scheduler/run_lifecycle.py`、`backend/app/modules/scheduler/orchestration.py`、`docs/scheduler-run-lifecycle.md`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `CREATE_QUEUED` | `QUEUED` | Job 存在且没有活动 run；计划时间有效。 | 设置 `next_dispatch_at`，保存 job/config 快照。 | 锁定 Job；活动 run 唯一索引和冲突映射防止重复创建。 |
| `(新建)` | `RECORD_CONFIGURATION_INVALID` | `FAILED` | scheduler 定义校验失败。 | 设置 `finished_at` 和配置错误分类；不进入队列。 | 使用 `require_no_active=False` 记录结果，不执行任务。 |
| `(新建)` | `RECORD_OVERLAPPING_ACTIVE_RUN` | `SKIPPED` | 已存在 `QUEUED` 或 `RUNNING` run。 | 设置 `finished_at` 和重叠分类；不进入队列。 | 活动 run 检查与唯一索引共同保证不重复执行。 |
| `QUEUED` | `CLAIM_DISPATCH` | `QUEUED` | `next_dispatch_at` 到期。 | 更新下一次 dispatch 租约时间。 | 行锁 `skip_locked`；重复扫描只能得到未被锁定的记录。 |
| `QUEUED` | `RELEASE_DISPATCH` | `QUEUED` | Celery 投递失败且仍是排队状态。 | 将下一次 dispatch 推迟到下一分钟。 | 锁定单行；非 `QUEUED` 记录无副作用返回。 |
| `QUEUED` | `CLAIM_EXECUTION` | `RUNNING` | 行锁成功，且运行未被取消。 | 设置开始时间和执行租约，清空 dispatch 时间并增加尝试次数。 | 有效 `RUNNING` 租约重复领取返回空；租约过期允许重新领取。 |
| `RUNNING` | `RECLAIM_EXPIRED_LEASE` | `RUNNING` | `lease_expires_at` 为空或已过期。 | 更新开始时间、租约和尝试次数。 | 行锁串行化领取；业务任务必须可承受至少一次执行。 |
| `RUNNING` | `FINISH_SUCCESS` | `SUCCEEDED` | orchestration 已成功领取并完成任务。 | 写入完成时间，清除租约和 dispatch 字段，清理成功告警。 | 结果落库后重复消息不应产生业务副作用；`finish_outcome()` 当前不自行重检状态。 |
| `RUNNING` | `FINISH_SKIP` | `SKIPPED` | 任务显式抛出受控跳过结果。 | 写入跳过分类、完成时间并清理租约。 | 只允许执行编排路径产生；终态重复调用应被视为无业务副作用。 |
| `RUNNING` | `FINISH_FAILURE` | `FAILED` | 配置或任务执行返回失败结果。 | 写入错误分类/摘要、完成时间并清理租约；必要时发送告警。 | 结果写入由生命周期边界集中处理；外部告警不在事务内。 |
| `QUEUED` | `CANCEL` | `CANCELLED` | 只取消尚未领取的运行。 | 写入完成时间并清除租约和 dispatch 字段。 | 批量取消锁定符合条件的排队记录；已领取记录不受影响。 |
| `SUCCEEDED`/`FAILED`/`SKIPPED`/`CANCELLED` | `ANY_LIFECYCLE_EVENT` | `不变/拒绝` | 终态不应再执行生命周期事件。 | 无。 | 文档契约视为终态；实现加固需另行任务。 |

### inventory.correction_request 状态迁移矩阵

来源：`backend/app/models/inventory.py:285-370`、`backend/app/modules/inventory/correction_service.py`、`.trellis/tasks/archive/2026-08/08-04-inventory-exception-correction/design.md`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `SUBMIT` | `PENDING_REVIEW` | 目标单据存在、非 legacy、有 ledger effect、时间戳匹配、提案和原因有效。 | 保存不可变提案、时间戳和 hash，写入创建审计。 | 锁定目标单据；活动申请部分唯一索引吸收并发提交。 |
| `PENDING_REVIEW` | `APPROVE` | `APPROVED` | 审核权限有效；目标仍存在且时间戳未改变。 | 原子创建 WorkItem 和初始 PENDING Attempt，写入审核人/时间并审计。 | Request 行锁；同一申请不可重复创建 WorkItem。 |
| `PENDING_REVIEW` | `REJECT` | `REJECTED` | 审核权限有效。 | 写入审核人/时间和拒绝审计。 | 行锁；非待审核状态拒绝迁移。 |
| `PENDING_REVIEW` | `WITHDRAW` | `WITHDRAWN` | 只能由申请人撤回，且仍待审核。 | 写入决定时间和撤回审计。 | 行锁；重复撤回为稳定冲突。 |
| `PENDING_REVIEW` | `APPROVE_STALE_TARGET` | `STALE` | 审核时目标更新时间已变化。 | 提交一个终态决定，不创建 WorkItem/Attempt。 | 这是业务结果，不是异常回滚；行锁保证单次决定。 |
| `APPROVED` | `APPLY_SUCCEEDED` | `APPLIED` | WorkItem/Attempt 成功，目标 token、提案 hash 和业务写入均有效。 | 与库存、WorkItem、Attempt、成功审计同一事务提交。 | 锁定相关对象；重复应用不重复产生库存副作用。 |
| `APPROVED` | `APPLY_TERMINAL_FAILURE` | `APPLICATION_FAILED` | 应用失败已分类为稳定失败。 | 与 WorkItem/Attempt 终结状态同一事务或独立失败事务完成。 | 失败类别稳定化；不把异常文本作为状态契约。 |
| `APPLICATION_FAILED` | `RECOVER` | `APPROVED` | 恢复权限有效；目标时间戳/hash 匹配；不存在其他活动申请。 | WorkItem 重新排队并创建下一序号 RECOVERY Attempt。 | 同时锁 Request、WorkItem、目标单据；冲突时状态和 Attempt 不变。 |
| `REJECTED`/`WITHDRAWN`/`STALE`/`APPLIED` | `ANY_REQUEST_EVENT` | `不变/拒绝` | 终态或当前事件不适用。 | 无。 | 非法迁移由领域服务稳定拒绝。 |

### inventory.correction_work_item 状态迁移矩阵

来源：`backend/app/models/inventory.py:372-470`、`backend/app/modules/inventory/correction_service.py`、`backend/app/modules/inventory/correction_attempts.py`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `CREATE_AFTER_APPROVAL` | `APPROVED_PENDING_APPLY` | Request 已批准且尚无 WorkItem。 | 保存处理类型、目标快照、hash 和当前 Attempt 序号。 | Request 行锁和 request 唯一约束防止重复 WorkItem。 |
| `APPROVED_PENDING_APPLY` | `CLAIM_ATTEMPT` | `RUNNING` | 当前 Attempt 为 PENDING；序号匹配；扫描批次可领取。 | 设置 WorkItem 租约；关联 scheduler run；Attempt 同步为 RUNNING。 | `FOR UPDATE SKIP LOCKED`；重复扫描不能重复领取。 |
| `RUNNING` | `APPLY_SUCCEEDED` | `SUCCEEDED` | WorkItem、Attempt、Request、目标单据均锁定且 token/hash 校验通过。 | 清租约；与 Request APPLIED、Attempt SUCCEEDED、库存和审计同事务提交。 | 重复执行发现非 RUNNING 或 scheduler run 不匹配时无副作用。 |
| `RUNNING` | `APPLY_TERMINAL_FAILURE` | `TERMINAL_FAILED` | 已分类为 `STALE_TARGET`、`NEGATIVE_BALANCE`、`EXECUTION_LOST` 或 `EXECUTION_FAILED`。 | 清租约，保存失败类别；Request APPLICATION_FAILED、Attempt TERMINAL_FAILED 联动。 | 失败终结单独短事务可提交；不自动重试。 |
| `TERMINAL_FAILED` | `RECOVER` | `APPROVED_PENDING_APPLY` | 恢复权限和目标 token/hash 校验通过，无其他活动申请。 | 清理终结字段，增加 Attempt 序号并创建 RECOVERY Attempt。 | 相关行加锁；冲突时保持原终结状态。 |
| `SUCCEEDED` | `ANY_WORK_ITEM_EVENT` | `不变/拒绝` | 成功是终态。 | 无。 | 重复任务投递无副作用。 |

### inventory.correction_attempt 状态迁移矩阵

来源：`backend/app/models/inventory.py:472-548`、`backend/app/modules/inventory/correction_attempts.py`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `CREATE_INITIAL` / `CREATE_RECOVERY` | `PENDING` | WorkItem 已创建或正在恢复；sequence 唯一。 | 记录来源和序号。 | `(work_item_id, sequence)` 唯一约束防止重复 Attempt。 |
| `PENDING` | `CLAIM` | `RUNNING` | 对应 WorkItem 为 APPROVED_PENDING_APPLY，且序号匹配。 | 写入 scheduler run、开始时间；WorkItem 同步为 RUNNING 并设置租约。 | 行锁和 skip-locked 保证单次领取。 |
| `RUNNING` | `APPLY_SUCCEEDED` | `SUCCEEDED` | 应用事务完成，目标单据 token/hash 校验通过。 | 写入完成时间并清除失败类别；联动 Request/WorkItem。 | Attempt 成功后不可再次应用。 |
| `RUNNING` | `APPLY_TERMINAL_FAILURE` / `LEASE_EXPIRED` | `TERMINAL_FAILED` | 失败类别已稳定化或执行租约已丢失。 | 写入完成时间和失败类别；WorkItem/Request 联动终结。 | 终态 Attempt 不被编辑、删除或重新领取；恢复创建新序号。 |
| `SUCCEEDED`/`TERMINAL_FAILED` | `ANY_ATTEMPT_EVENT` | `不变/拒绝` | Attempt 终态不可逆。 | 无。 | 重复 worker 消息安全返回。 |

### email.outbox 状态迁移矩阵

来源：`backend/app/models/email.py:32-38`、`backend/app/services/email_outbox.py`、`.trellis/tasks/archive/2026-07/07-27-generic-email-outbox/design.md`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `QUEUE` | `PENDING` | 邮件 payload 或 link kind 合法。 | 设置首次 `next_attempt_at`。 | producer flush 后由外层事务提交；不重复生成同一业务邮件由 producer 保证。 |
| `PENDING`/`RETRY_WAIT` | `CLAIM_DELIVERY` | `LEASED` | 到期、未达到 8 次上限、渲染和收件人校验成功。 | 增加尝试次数，设置 lease，生成事务外 SMTP payload。 | 行锁；有效 lease 期间重复领取无副作用。 |
| `PENDING`/`RETRY_WAIT` | `REJECT_UNDELIVERABLE` | `FAILED` | recipient、用户、模板或版本快照校验失败，或达到最大尝试次数。 | 写入失败时间和稳定错误类别。 | 终态重复扫描无副作用。 |
| `LEASED` | `DELIVER_SUCCESS` | `DELIVERED` | 结果 payload 的 outbox ID 和 lease 到期时间完全匹配。 | 清 lease，写入 delivered 时间并清除错误。 | `FOR UPDATE` 加 lease token 比较；旧 worker 结果被忽略。 |
| `LEASED` | `DELIVER_FAILURE` | `RETRY_WAIT` | 发送失败且尝试次数未达上限。 | 清 lease，保存错误类别和 15 分钟后重试时间。 | 结果只接受当前 lease；重复失败不重复计数。 |
| `LEASED` | `DELIVER_FAILURE` / `RECOVER_EXPIRED_LEASE` | `FAILED` | 发送失败或租约过期且尝试次数达到 8 次。 | 清 lease，写入 failed 时间和错误类别。 | 过期租约由行锁扫描恢复；终态不会再次领取。 |
| `DELIVERED`/`FAILED` | `ANY_DELIVERY_EVENT` | `不变/拒绝` | 已是终态。 | 无。 | 重复 worker 消息必须是幂等 no-op。 |

### inventory.daily_report 状态迁移矩阵

来源：`backend/app/models/inventory.py:54-58`、`backend/app/modules/inventory/daily_report.py`、`.trellis/tasks/archive/2026-07/07-25-celery-redis-runtime/prd.md`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `CREATE_SNAPSHOT` | `PENDING` | 当前时间在上海 08:00-08:15 窗口；加工单位启用。 | 固化库存快照，设置收件人解析下一次尝试时间。 | `(processing_unit_id, business_date)` 唯一约束吸收重复创建。 |
| `PENDING`/`RETRY_WAIT` | `RESOLVE_RECIPIENTS` | `PENDING` | 找到收件人。 | 创建独立 Delivery 行，记录解析时间并清错误。 | 行锁；重复解析不重复创建相同邮箱 delivery。 |
| `PENDING`/`RETRY_WAIT` | `RECIPIENTS_MISSING` | `RETRY_WAIT` | 没有收件人且解析次数未达上限。 | 增加解析次数，写错误类别和下一次尝试时间。 | 行锁；达到上限后改为 FAILED。 |
| `PENDING`/`RETRY_WAIT` | `RECIPIENTS_MISSING` | `FAILED` | 没有收件人且解析次数已达上限。 | 保存失败类别和更新时间。 | 失败日报不会被继续解析。 |
| `PENDING`/`RETRY_WAIT` | `ROLLUP_DELIVERIES` | `DELIVERED` | 所有 Delivery 为 DELIVERED。 | 清除 Report 错误并更新摘要时间。 | 在 Delivery 结果事务内刷新；重复刷新无副作用。 |
| `PENDING`/`RETRY_WAIT` | `ROLLUP_DELIVERIES` | `RETRY_WAIT` | 至少有 Delivery 仍待处理、投递中或重试等待。 | 保留可重试 Report。 | 同一 Report 的 Delivery 集合查询与状态刷新在事务内完成。 |
| `PENDING`/`RETRY_WAIT` | `ROLLUP_DELIVERIES` | `FAILED` | Delivery 全部为终态且至少一个失败。 | 将 Report 置为失败摘要。 | 终态摘要不应被重复任务逆转。 |
| `DELIVERED`/`FAILED` | `ANY_REPORT_EVENT` | `不变/拒绝` | Report 已达到终态。 | 无。 | 重复创建/重试任务不能改变终态。 |

### inventory.daily_report_delivery 状态迁移矩阵

来源：`backend/app/models/inventory.py:614-678`、`backend/app/modules/inventory/daily_report.py`。

| 当前状态 | 事件 | 目标状态 | 前置条件 | 副作用 | 幂等/并发语义 |
| --- | --- | --- | --- | --- | --- |
| `(新建)` | `CREATE_RECIPIENT_DELIVERY` | `PENDING` | Report 收件人解析成功。 | 保存邮箱和首次尝试时间。 | Report/email 唯一约束防止重复收件人行。 |
| `PENDING`/`RETRY_WAIT` | `CLAIM_DELIVERY` | `DELIVERING` | 到期且尝试次数未达 8 次。 | 增加尝试次数，设置 delivery lease，提交后执行 SMTP。 | 行锁；有效投递 lease 期间重复领取无副作用。 |
| `PENDING`/`RETRY_WAIT` | `MAX_ATTEMPTS_EXCEEDED` | `FAILED` | 领取前发现达到最大次数。 | 保存失败类别并清除 lease；刷新 Report 摘要。 | 行锁；终态重复任务无副作用。 |
| `DELIVERING` | `DELIVER_SUCCESS` | `DELIVERED` | SMTP 调用成功。 | 写入 delivered 时间并清除 lease/错误；刷新 Report。 | 结果落库独立短事务；重复结果不会重复发送。 |
| `DELIVERING` | `DELIVER_FAILURE` | `RETRY_WAIT` | SMTP 未配置或发送异常，且次数未达上限。 | 清 lease，保存错误类别和下一次尝试时间；刷新 Report。 | 领取、SMTP、结果落库三段事务；结果失败不回滚外部发送。 |
| `DELIVERING` | `LEASE_EXPIRED` / `DELIVER_FAILURE` | `FAILED` | 租约过期或发送失败且已达 8 次。 | 清 lease，保存失败类别；刷新 Report。 | 扫描用行锁和 skip-locked；过期 worker 的迟到结果不应覆盖新状态。 |
| `DELIVERED`/`FAILED` | `ANY_DELIVERY_EVENT` | `不变/拒绝` | Delivery 已是终态。 | 无。 | 重复 retry 任务无副作用。 |

## 4. 为什么不新增数据库表

这里的矩阵是设计规则和代码边界，不是运行时数据。数据库继续保存当前状态，PostgreSQL enum、CHECK、唯一索引、行锁、租约字段和既有审计记录继续负责持久化与一致性。把静态边放进表会增加表版本、动态解释器、权限和迁移复杂度，却不能替代领域前置条件和跨表事务。

只有出现以下需求，才重新评估工作流定义/迁移关系表：管理员动态配置流程；同一对象使用不同版本的流程定义；需要独立长期查询迁移历史；或多个领域确实复用相同的审批人、待办、超时、升级和恢复运行时。当前项目没有这些条件。

## 5. 可读性、采用顺序与非目标

中心文档不使用 `ALL_TRANSITIONS` 式嵌套全局字典，而按领域和聚合分节。新增领域只增加自己的小表，不扩大既有矩阵；多表工作流按独立生命周期拆表，由领域服务说明联动关系。

采用顺序：先执行本任务的规范和文档回填；后续如有收益，再选库存纠错或其他单一领域补充代码校验与迁移测试；最后才评估是否存在通用工作流运行时的真实复用。

本任务不改调度器、库存纠错、Email Outbox、日报运行时代码，不改 schema、Alembic、API、前端或生成客户端，不引入 `transitions`、`python-statemachine`、Temporal 或通用审批 UI。后续工作见 `.trellis/tasks/08-10-unified-state-transition/deferred-iterations.md`。
