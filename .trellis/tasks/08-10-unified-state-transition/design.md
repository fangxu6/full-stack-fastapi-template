# 统一状态迁移设计

## 目标与边界

本任务建立可执行的设计约定，而不是引入一个状态机运行时。每个领域继续拥有自己的状态、事件、权限、事务和副作用；项目统一的是在何时编写状态迁移矩阵、矩阵的命名和最小内容，以及测试应验证的边界。

矩阵是设计文档中的静态契约，不是数据库表，也不要求转换为共享 Python 常量。只有当某个领域确实需要用声明式规则校验结构性迁移时，才可在该领域内部定义 `<AGGREGATE>_TRANSITIONS`。本任务不得新增 `ALL_TRANSITIONS`、注册中心、审批表、工作流定义表、第三方状态机库或运行时代码改造。

`enum` 与矩阵不冲突：`StrEnum` 定义稳定且封闭的序列化值，矩阵定义生命周期状态由领域事件触发的合法边。类别、来源、策略、角色和错误分类只使用枚举；当前值会约束后续业务行为的工作流状态才需要矩阵。

## 规范载体与来源

`docs/state-machine-unified-transition-design.md` 是以下矩阵的唯一规范载体：

1. `scheduler.scheduler_run 状态迁移矩阵`
2. `inventory.correction_request 状态迁移矩阵`
3. `inventory.correction_work_item 状态迁移矩阵`
4. `inventory.correction_attempt 状态迁移矩阵`
5. `email.outbox 状态迁移矩阵`
6. `inventory.daily_report 状态迁移矩阵`
7. `inventory.daily_report_delivery 状态迁移矩阵`

每张表固定使用 `当前状态`、`事件`、`目标状态`、`前置条件`、`副作用`、`幂等/并发语义` 六列。`(新建)` 仅表示对象首次持久化，不是一个可存储状态；允许的自循环必须显式写出。名称中的第二段是拥有该独立生命周期的持久化对象，即使它是父聚合管理的子实体。

以当前运行时代码为事实来源，旧设计和 ADR 仅作解释来源。若实现只依赖调用方前置条件而未在写入函数内重检，矩阵必须如实标注该事实，不能把文档写成不存在的代码保证。归档 Trellis 任务和 ADR 不作回填修改。

## 回填矩阵内容

### scheduler.scheduler_run

来源：`backend/app/models/scheduler.py`、`backend/app/modules/scheduler/run_lifecycle.py`、`backend/app/modules/scheduler/orchestration.py`、`docs/scheduler-run-lifecycle.md`。

| 当前状态 | 事件 | 目标状态 | 核心边界 |
| --- | --- | --- | --- |
| `(新建)` | `QUEUE` | `QUEUED` | 记录 `next_dispatch_at`；同一 job 只能有一个 `QUEUED` 或 `RUNNING` run。 |
| `(新建)` | `RECORD_PRE_EXECUTION_OUTCOME` | `FAILED` / `SKIPPED` / `CANCELLED` | 仅记录已知未执行结果；写入 `finished_at`。 |
| `QUEUED` | `CLAIM_EXECUTION` | `RUNNING` | 行锁领取，清空 dispatch 时间，设置执行租约并增加尝试次数。 |
| `RUNNING` | `RECLAIM_EXPIRED_LEASE` | `RUNNING` | 仅租约已过期；重新设置租约并增加尝试次数。 |
| `RUNNING` | `FINISH_SUCCESS` / `FINISH_SKIP` / `FINISH_FAILURE` | `SUCCEEDED` / `SKIPPED` / `FAILED` | 清理租约和 dispatch 字段，写入结果与完成时间。 |
| `QUEUED` | `CANCEL` | `CANCELLED` | 仅取消排队 run；写入完成时间并清理租约/dispatch。 |

`SUCCEEDED`、`FAILED`、`SKIPPED`、`CANCELLED` 是预期终态。矩阵会注记 `finish_outcome()` 当前由 orchestration 的成功领取路径约束，但函数自身没有状态重检；这是后续实现任务可评估的加固点，不在本任务修改。

### inventory.correction_request、work_item 与 attempt

来源：`backend/app/models/inventory.py`、`backend/app/modules/inventory/correction_service.py`、`backend/app/modules/inventory/correction_attempts.py`、`.trellis/tasks/archive/2026-08/08-04-inventory-exception-correction/design.md`。

| 生命周期对象 | 关键边 |
| --- | --- |
| `correction_request` | `(新建) -> PENDING_REVIEW`；`PENDING_REVIEW -> APPROVED/REJECTED/WITHDRAWN/STALE`；`APPROVED -> APPLIED/APPLICATION_FAILED`；`APPLICATION_FAILED -> APPROVED`。 |
| `correction_work_item` | `(新建) -> APPROVED_PENDING_APPLY`；`APPROVED_PENDING_APPLY -> RUNNING`；`RUNNING -> SUCCEEDED/TERMINAL_FAILED`；`TERMINAL_FAILED -> APPROVED_PENDING_APPLY`。 |
| `correction_attempt` | `(新建) -> PENDING`；`PENDING -> RUNNING`；`RUNNING -> SUCCEEDED/TERMINAL_FAILED`。终态 attempt 不恢复，恢复时创建下一 sequence 的新 attempt。 |

三个矩阵必须分别列出前置条件和跨表副作用：审批原子创建 work item 与 initial attempt；claim 同时领取 work item 与 attempt；成功或终结在同一事务更新 request、work item、attempt 和必要的库存/审计记录；恢复创建新 attempt。行锁、预期更新时间、proposal hash、活跃申请唯一约束和 scheduler-run 对应关系必须写入相应的幂等/并发列。

### email.outbox

来源：`backend/app/models/email.py`、`backend/app/services/email_outbox.py`、`.trellis/tasks/archive/2026-07/07-27-generic-email-outbox/design.md`。

| 当前状态 | 事件 | 目标状态 | 核心边界 |
| --- | --- | --- | --- |
| `(新建)` | `QUEUE` | `PENDING` | 设置首次尝试时间。 |
| `PENDING` / `RETRY_WAIT` | `CLAIM_DELIVERY` | `LEASED` | 到期且未超最大次数，行锁后增加尝试次数、创建租约。 |
| `PENDING` / `RETRY_WAIT` | `REJECT_UNDELIVERABLE` | `FAILED` | 最大次数已尽或渲染/收件人校验失败。 |
| `LEASED` | `DELIVER_SUCCESS` | `DELIVERED` | 结果必须持有同一有效 lease token。 |
| `LEASED` | `DELIVER_FAILURE` / `RECOVER_EXPIRED_LEASE` | `RETRY_WAIT` / `FAILED` | 清理租约；按尝试次数决定重试或终结。 |

重复领取、过期前重复结果以及终态重复投递都是无副作用返回；结果写入必须比较 payload 中的 lease 过期时间，不能只比较状态。

### inventory.daily_report 与 daily_report_delivery

来源：`backend/app/models/inventory.py`、`backend/app/modules/inventory/daily_report.py`、`.trellis/tasks/archive/2026-07/07-25-celery-redis-runtime/prd.md`。

| 生命周期对象 | 关键边 |
| --- | --- |
| `daily_report` | `(新建) -> PENDING`；`PENDING/RETRY_WAIT -> RETRY_WAIT/FAILED`（收件人缺失并按解析尝试次数决定）；`PENDING/RETRY_WAIT -> PENDING`（收件人解析成功，创建 delivery）；按全部 delivery 的聚合结果转为 `DELIVERED`、`RETRY_WAIT` 或 `FAILED`。 |
| `daily_report_delivery` | `(新建) -> PENDING`；`PENDING/RETRY_WAIT -> DELIVERING`；`DELIVERING -> DELIVERED/RETRY_WAIT/FAILED`；到期租约恢复为 `RETRY_WAIT/FAILED`；领取前发现达到上限可直接转 `FAILED`。 |

日报 Report 的状态是 Delivery 集合的派生摘要，不能独立于 Delivery 写入；所有 delivery 领取和结果写入都使用行锁，Report 刷新与被影响的 Delivery 在同一事务中完成。重复日报创建由 `(processing_unit_id, business_date)` 唯一约束吸收，重复/过早 delivery 任务无副作用返回。

## 规则文件设计

新增 `.trellis/spec/backend/state-transition-guidelines.md`，采用 code-spec 七段结构：范围/触发条件、签名命名、领域契约、验证与错误矩阵、Good/Base/Bad、所需测试、Wrong vs Correct。规则明确：

- 触发条件是有限工作流状态加事件、终态、租约、重试/恢复、并发或跨实体协调，而不是任意 enum。
- `<Aggregate>State` 与 `<Aggregate>Event` 是新命名首选；现有语义准确的 `<Aggregate>Status` 保留。事件是领域动词，持久化与否由领域决定。
- 设计文档采用 `## 状态迁移矩阵（State Transition Matrix）` 和 `<领域>.<聚合> 状态迁移矩阵`；可选代码规则常量只能在领域内以 `<AGGREGATE>_TRANSITIONS` 命名。
- 矩阵只表达结构边；权限、锁、版本、事务、跨表副作用、审计、重试和恢复必须填入矩阵列并继续由领域服务实现。
- 测试至少覆盖合法边、非法边、终态、适用的恢复/重试、幂等和并发边界。
- 禁止全局状态枚举、`ALL_TRANSITIONS` 和可执行跨领域回调的注册中心。

`backend/index.md` 链接新规则；`database-guidelines.md` 在持久化业务状态场景链接新规则；`directory-structure.md` 在模块升级规则中要求满足触发条件的设计带矩阵。不要修改由 `08-07-correct-scheduler-lifecycle-spec` 所有的 `async-task-guidelines.md`。

## 兼容性、风险与回滚

本任务只修改 Markdown、spec 目录索引和规范日志，不改应用行为、API、数据库 schema、Alembic 或生成客户端，因此不存在数据迁移或运行时回滚。主要风险是把当前实现的调用约束误写成函数内强制校验，或将多对象流程压成一张矩阵；实施时逐行以源码和既有测试核对，并在矩阵中分开写结构边与前置条件。

若文档或规则有误，直接回退本任务的 Markdown 提交；不得借此回退或改写历史 ADR、归档任务或活跃 `08-07` 任务。

## 任务拆分

不创建子任务。方案文档、规则文件、索引与规范日志共享同一验收条件，拆分反而会造成矩阵命名和规则语义不同步。将来把某个领域改造成矩阵驱动代码、收紧 scheduler 终态校验或评估通用工作流运行时，均须创建独立任务并遵守延期记录。
