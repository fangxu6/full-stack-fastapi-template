# Scheduler Run Lifecycle

本文说明 scheduler 运行生命周期中的 `claim`、`finish` 和 `lease`。

## 执行流程

```text
QUEUED
  -> claim
RUNNING + lease
  -> execution.execute()
SUCCEEDED / SKIPPED / FAILED
  -> finish_outcome
```

实现位置：[`backend/app/modules/scheduler/run_lifecycle.py`](../backend/app/modules/scheduler/run_lifecycle.py)

## claim：领取执行权

Worker 开始执行前调用 `claim_execution()`：

- 使用数据库行锁读取 `SchedulerRun`。
- 只有 `QUEUED` 或租约已过期的 `RUNNING` 才能继续执行。
- 将状态设置为 `RUNNING`。
- 写入 `started_at`。
- 设置 `lease_expires_at`。
- 增加 `attempt_count`。

`claim` 解决的是执行权竞争问题。Celery 消息重复投递时，多个 Worker 不能同时领取同一个有效 run。

## finish：记录最终结果

业务执行完成后，`execution.execute()` 返回 `SchedulerRunOutcome`，Worker
再调用 `finish_outcome()`：

- 写入 `SUCCEEDED`、`SKIPPED` 或 `FAILED`。
- 保存错误分类和错误摘要。
- 写入 `finished_at`。
- 清除 `lease_expires_at`。
- 清除 `next_dispatch_at`。

`finish` 让所有终态写入经过同一条路径，避免不同执行入口漏清租约字段或写出不一致状态。

`execution.execute()` 只负责冻结任务类解析、配置校验、任务调用和结果
分类。它不接收数据库 Session，不提交事务，也不发送告警。

## lease：临时执行租约

`lease_expires_at` 表示执行权的有效期，不表示 Worker 在整个业务执行期间一直持有数据库锁。

例如：

```text
10:00:00 Worker A claim
10:00:00 lease_expires_at = 10:05:00
10:02:00 Worker A 崩溃
10:05:00 租约过期
10:05:01 Worker B 可以重新 claim
```

租约用于处理 Worker 崩溃、进程重启或消息重新投递的情况，避免任务永久停留在 `RUNNING`。

## 三者的关系

```text
claim = 谁拿到执行权
lease = 执行权有效多久
execution = 任务执行结果如何分类
finish_outcome = 结果如何落库并释放执行权
```

租约过期后允许重新执行，因此系统具有至少一次执行语义。业务任务仍应保持幂等，避免重试或重复投递造成重复业务数据或重复外部副作用。

## 参考实现

- `claim_execution()`：集中处理状态检查、行锁和租约设置。
- `finish_outcome()`：集中处理终态、错误信息和租约清理。
- `tasks.execute_run()`：负责 claim、事务提交、调用 `execution.execute()`、
  终态持久化和告警编排。
