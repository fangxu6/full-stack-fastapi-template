# prod：计划任务运行时

## 目标与非目标

提供可配置任务的登记、调度、执行、租约、重试、超时和运维告警。模板已有 `SchedulerJob`、`SchedulerRun` 和 `backend/app/modules/scheduler/`，本能力的决策是复用并补契约，不搬运另一套实现。非目标是允许任意用户提交 Python 类路径。

## 所有权与状态

Scheduler 拥有 Job/Run 生命周期；业务任务拥有自身业务事实。Run 至少区分 `QUEUED -> RUNNING -> SUCCEEDED|FAILED|SKIPPED|CANCELLED`，主动触发与定时触发区分 requester。一个 Job 的活动 Run、租约和 attempt 受数据库条件约束保护。

## 调度、幂等与恢复

Beat/调度同步不得每次覆盖真实 last-run 基线；只对缺失基线初始化。成功发布到 Broker 只表示 Run 仍待 Worker 执行，Worker 才能写开始/终态。租约过期可回收，重试按错误类别和上限退避；陈旧 Worker 用条件更新拒绝覆盖新 Run。

## 安全、观测与配置

任务注册为服务端白名单，载荷只传 ID/JSON，权限区分查看、手动运行、重试、取消和管理。记录 run、task、attempt、租约、队列延迟、错误摘要和 trace；告警区分失败、积压、重叠、配置错误和 Worker 不可用。Broker、并发、超时和保留期按环境配置。

## 迁移、测试、发布与回滚

迁移先建 Job/Run 表和索引，再接入一个任务；历史调度记录只读兼容。测试覆盖同步幂等、last-run 基线、重复派发、发布失败、Worker 崩溃、租约回收、超时、手动触发权限和终态不可逆。回滚停用新注册任务，保留运行记录和可恢复队列。

## 来源与禁止复制

来源：[`012d8658`](../backend-2026-05-07-012d8658.md)、[`0350dc41`](../backend-2026-05-08-0350dc41.md)、[`c978b4b6`](../backend-2026-05-08-c978b4b6.md)、[`a3b3ddff`](../backend-2026-07-15-a3b3ddff.md)、[`14910a94`](../backend-2026-07-15-14910a94.md)、[`2cebb894`](../backend-2026-07-21-2cebb894.md)、[`2c373c2c`](../frontend-2026-05-07-2c373c2c.md)、[`8978bbe5`](../frontend-2026-05-08-8978bbe5.md)。

禁止用启动副作用预置生产数据、把 `send_task()` 当执行成功、在任务中携带 ORM/session，或让 UI 自己推断运行状态。
