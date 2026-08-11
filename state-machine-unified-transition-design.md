# 统一状态迁移规则方案

## 文档用途

本文档整理当前项目关于状态机统一方案的讨论结果，作为后续创建开发任务的上下文输入。

本文档是设计讨论稿，不代表已经批准实施，也不创建 Trellis 开发任务。

## 1. 结论摘要

当前项目已经存在多套领域状态机，但没有统一的状态机引擎：

- 调度运行有 `QUEUED -> RUNNING -> SUCCEEDED/FAILED/SKIPPED/CANCELLED` 生命周期。
- 库存纠错有申请、工作项、Attempt 三条相互联动的状态轨迹。
- 邮件 Outbox 和库存日报有租约、重试、成功、失败状态。
- 认证会话通过 `expires_at` 和 `revoked_at` 表达有效生命周期，但没有显式状态枚举。

推荐采用方案一：

> 统一状态迁移规则、并发控制、审计和测试方式；保留每个领域自己的状态和事件，不建设全局状态矩阵或通用工作流引擎。

该方案的核心不是把所有领域变成同一套状态，而是让不同领域遵守同一套迁移契约。

## 2. 当前代码现实

### 2.1 调度运行

`SchedulerRunStatus` 定义在 `backend/app/models/scheduler.py:26-32`。

当前生命周期集中在 `backend/app/modules/scheduler/run_lifecycle.py`：

- `create_run()` 创建 `QUEUED` 运行记录，也允许配置错误或重叠运行直接生成终态记录。
- `claim_execution()` 将可执行的 `QUEUED` 或租约过期的 `RUNNING` 记录置为 `RUNNING`。
- `finish_outcome()` 持久化执行结果。
- `cancel_queued_runs()` 将排队记录置为 `CANCELLED`。

项目已有规划文档明确要求 `run_lifecycle.py` 作为 `SchedulerRun` 生命周期字段的唯一修改边界，见 `.trellis/tasks/08-07-correct-scheduler-lifecycle-spec/prd.md`。

### 2.2 库存纠错

状态定义在 `backend/app/models/inventory.py:75-96`：

- 申请：`PENDING_REVIEW`、`APPROVED`、`REJECTED`、`WITHDRAWN`、`STALE`、`APPLIED`、`APPLICATION_FAILED`。
- 工作项：`APPROVED_PENDING_APPLY`、`RUNNING`、`SUCCEEDED`、`TERMINAL_FAILED`。
- Attempt：`PENDING`、`RUNNING`、`SUCCEEDED`、`TERMINAL_FAILED`。

主要迁移由以下模块负责：

- `backend/app/modules/inventory/correction_service.py`：创建、审批、驳回、撤回、恢复。
- `backend/app/modules/inventory/correction_attempts.py`：领取、执行、成功和失败终结。

这个领域不是单表状态机。一次审批或执行可能同时更新申请、工作项和 Attempt，因此不能仅靠一个通用状态字段或一个通用回调完成。

### 2.3 邮件和日报投递

邮件状态定义在 `backend/app/models/email.py:32-38`：

```text
PENDING -> LEASED -> DELIVERED
                   -> RETRY_WAIT -> LEASED
                   -> FAILED
```

库存日报分别维护 Report 和 Delivery 状态：

```text
Report:    PENDING -> DELIVERED / RETRY_WAIT / FAILED
Delivery:  PENDING -> DELIVERING -> DELIVERED / RETRY_WAIT / FAILED
```

这些状态本质上是可靠投递状态机，重点是租约、最大尝试次数、幂等和失败重试，而不是审批流程。

### 2.4 库存导入和认证会话

`InventoryImportBatch` 只有来源指纹、导入器版本、报告和 `imported_at`，没有状态字段，当前不应强行抽象成状态机，见 `backend/app/models/inventory.py:200-214`。

`AuthSession` 通过创建记录、过期时间和撤销时间表达生命周期，认证校验集中在 `backend/app/modules/auth/session.py`。它是访问会话生命周期，不应和库存审批、调度运行共用状态枚举。

## 3. 方案一：领域独立状态 + 共享最小迁移机制

### 3.1 统一什么

各领域统一以下迁移契约：

```text
当前状态 + 领域事件 -> 目标状态
```

迁移执行还需要统一处理：

1. 当前状态校验。
2. 非法迁移异常。
3. 事务边界。
4. 并发锁或版本校验。
5. 幂等语义。
6. 审计记录格式。
7. 状态迁移测试方式。

### 3.2 不统一什么

以下内容必须由领域自己拥有：

- 状态枚举。
- 事件枚举或领域命令。
- 状态迁移矩阵。
- 业务前置条件。
- 跨表副作用。
- 重试、恢复和终态语义。

例如，调度的 `RUNNING` 代表执行租约，库存纠错的 `RUNNING` 代表工作项执行，邮件的 `LEASED` 代表投递租约。它们名称相似，但语义不相同，不能合并。

### 3.3 领域内迁移矩阵

每个领域维护自己的小型矩阵，而不是建立一个全局矩阵：

```python
CORRECTION_REQUEST_TRANSITIONS = {
    "PENDING_REVIEW": {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "withdraw": "WITHDRAWN",
    },
    "APPROVED": {
        "apply": "APPLIED",
    },
}
```

推荐的组织方式是：

```text
inventory/correction_states.py
scheduler/run_lifecycle.py
services/email_outbox.py
```

状态和事件都在所属领域内定义，避免全局注册表、跨领域命名冲突和类型混乱。

### 3.4 迁移矩阵的边界

矩阵只描述结构性允许关系，不取代业务前置条件。

例如，库存纠错的审批可以有以下结构性关系：

```text
PENDING_REVIEW + approve -> APPROVED
```

但审批前仍需由领域服务检查：

- 目标单据是否仍然存在。
- 目标时间戳是否发生变化。
- 申请是否仍处于待审核状态。
- 申请人和审核人权限是否正确。

因此实际执行顺序应是：

```text
获取锁
检查领域前置条件
校验迁移矩阵
更新领域对象
执行跨表副作用
写审计
提交事务
```

### 3.5 多表状态机的处理方式

对于库存纠错，不应把申请、工作项和 Attempt 压成一张通用矩阵。

推荐由 `correction_service.py` 和 `correction_attempts.py` 保留领域命令：

```text
approve_request()
reject_request()
withdraw_request()
recover_work_item()
claim_pending_attempts()
apply_claimed_attempt()
finalize_failed_attempt()
```

这些命令内部使用各自的局部迁移规则，并在一个事务中维护三类对象的一致性。

## 4. 对关键疑问的结论

### 4.1 维护迁移矩阵是否需要新增数据库表

不需要。

这里的迁移矩阵是代码中的规则定义，不是数据库表，也不是 Alembic migration。

现有数据库继续保存当前状态：

```text
inventory_correction_request.status = APPROVED
```

代码矩阵负责判断：

```text
当前状态 + 事件是否允许，以及目标状态是什么
```

现有 PostgreSQL ENUM、CHECK 约束、部分索引、行锁和审计表继续承担持久化和一致性职责。

只有在以下需求出现时，才需要新增工作流定义或迁移关系表：

- 管理员需要动态配置流程。
- 同一业务对象需要使用不同版本的流程定义。
- 状态迁移历史必须独立于现有审计表长期查询。
- 需要通用审批人、待办、超时和工作项运行时。

当前项目没有这些必要条件，不应提前建设。

### 4.2 各领域状态和事件不同，矩阵会不会越来越大

如果设计成一个全局矩阵，会越来越大且难以阅读。因此不采用：

```python
ALL_TRANSITIONS = {
    "inventory_correction": {...},
    "scheduler": {...},
    "email": {...},
}
```

正确方式是“每个聚合根一张小矩阵”：

```text
CorrectionRequestState + CorrectionRequestEvent
SchedulerRunStatus + SchedulerRunEvent
EmailOutboxStatus + EmailOutboxEvent
```

新增领域只增加一个局部规则文件，不扩大已有领域的矩阵。

同时，不是每个领域都必须使用矩阵：

- 状态少、迁移简单：使用带前置条件的领域方法。
- 状态和事件较多：使用领域内迁移矩阵。
- 多表联动、恢复复杂：使用显式领域 Service 命令。

统一框架只提供最小机制，不能强迫所有领域都套同一套形式。

## 5. 方案边界和非目标

### 本方案包含

- 领域状态和事件的命名约定。
- 领域内迁移规则的组织方式。
- 非法迁移、并发、幂等和审计的共同契约。
- 状态迁移矩阵的测试约定。
- 在现有数据库结构上的渐进式接入方式。

### 本方案不包含

- 新增通用工作流数据库表。
- 引入 `transitions`、`python-statemachine` 等第三方库。
- 引入 Temporal 或其他外部工作流运行时。
- 把所有领域状态合并为一个公共枚举。
- 一次性重构调度、库存纠错、邮件和日报全部代码。
- 将前端 React Query 的请求状态当作后端业务状态机。

## 6. 备选方案及暂不采用原因

### 6.1 Python 状态机库

`transitions` 或 `python-statemachine` 可以提供声明式状态定义，但不能自动解决：

- 数据库事务。
- `SELECT FOR UPDATE`。
- 多表一致性。
- Celery 租约和重试。
- 现有审计契约。

引入依赖后，仍需要保留大量领域代码，当前收益不足以抵消依赖和调试成本。

### 6.2 通用数据库工作流引擎

需要引入工作流实例、定义、迁移、任务、版本和权限等模型，会把当前问题扩大为一个新的平台产品。

当前 Trellis 规划已经明确：应先完成具体库存业务流程，再评估是否存在足够稳定的通用工作流边界。

### 6.3 Temporal

Temporal 适合长时间运行、跨服务、等待外部回调和可靠定时器场景。当前项目已有 Celery 调度和 Outbox 机制，直接引入会形成两套执行体系。

只有当业务流程确实需要跨天等待、外部回调编排或复杂补偿时，才重新评估。

## 7. 推荐落地顺序

### 第一步：先统一契约，不改数据库

- 约定领域事件使用业务动词，例如 `approve`、`apply`、`claim`、`deliver`。
- 每个领域明确允许迁移、终态、可恢复状态和幂等行为。
- 明确状态变更的唯一 Service 边界。

### 第二步：选择一个领域试点

库存纠错最适合作为试点，因为它同时包含审批、工作项、Attempt、租约、失败和恢复。

试点不应一次性抽象所有领域，而应验证：

- 局部矩阵是否足够清晰。
- 多表状态迁移是否仍由领域 Service 控制。
- 审计、锁和幂等契约是否可复用。
- 测试是否比当前直接赋值更容易维护。

### 第三步：按收益迁移其他领域

- 调度器优先保持 `run_lifecycle.py` 的集中边界，只补充统一契约和迁移测试。
- 邮件 Outbox 只在统一重试、租约和幂等规则确实减少重复后再接入。
- 日报投递不应为了形式统一而强行改造。

### 第四步：重新评估是否需要通用运行时

只有多个领域实际复用了相同的角色、待办、超时、升级和恢复机制，才进入通用工作流平台设计。

## 8. 后续开发任务的建议边界

后续开发任务建议先聚焦“统一迁移契约和库存纠错试点”，不要把所有领域重构写进一个任务。

### 建议目标

建立领域独立、机制统一的状态迁移模式，并用库存纠错验证。

### 建议验收标准

- 每个库存纠错聚合都有明确的状态、事件和允许迁移清单。
- 非法迁移能够在领域服务层被拒绝。
- 多表迁移仍在同一事务中完成。
- 并发领取和重复执行不会产生重复副作用。
- 成功、失败、恢复和终态行为有迁移矩阵测试。
- 审计能够记录操作人、事件、对象和结果。
- 不新增通用工作流表和第三方状态机依赖。
- 调度器、邮件和日报的现有行为不发生回归。

### 不应放入首个任务

- 全局状态机注册中心。
- 动态配置工作流。
- 通用审批 UI。
- Temporal 或其他工作流平台接入。
- 一次性迁移所有现有状态字段。

## 9. 待创建任务前需要确认的问题

1. 是否以库存纠错作为第一试点领域。
2. 是否需要把 `from_state`、`event`、`to_state` 纳入现有审计事件结构。
3. 迁移规则是否采用字典矩阵，还是对复杂聚合只保留领域命令。
4. 首个任务是否只做契约、测试和一个试点，不改其他领域。

在这些问题确认前，不应创建通用工作流表或选择第三方状态机框架。
