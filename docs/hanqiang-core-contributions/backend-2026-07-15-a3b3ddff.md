# Celery Beat 同步持久化上次运行基线

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)
> 定时任务聚合指南：[通用定时任务平台复用指南](scheduled-task-reusable-guide.md)

## 1. 提交定位

- 仓库：`backend/JSECommon`
- 完整 SHA：`a3b3ddff1bd932166d7b16973e743fe975ad34a6`
- 父提交：`3385080ade802ceb69580545e12556197ee1f6f3`
- 作者：`hanqiang <240448317@qq.com>`
- 时间：`2026-07-15 08:37:14 +08:00`
- 原始主题：`fix(scheduled-task): persist beat last-run baseline`
- 变更规模：3 个文件，新增 225 行、删除 2 行

该提交修复动态同步 Celery Beat 任务时的时间基线问题：新建 `PeriodicTask` 时写入 `last_run_at=now`，已有记录仅在 `last_run_at` 为空时回填。之后的全量同步不会用同步时刻覆盖 Beat 已经记录的上次运行时间，避免午夜重载、配置更新或服务重启改变 Cron 的 due 判断。

## 2. 变更文件地图

| 文件 | 变更 | 可复用职责 |
| --- | --- | --- |
| `app/services/scheduled_task/beat_scheduler_service.py` | 新任务初始化 `last_run_at`；既有任务只回填空值；保留稳定名称、Cron、参数和启停同步。 | 将业务任务定义幂等同步到 `celery_sqlalchemy_scheduler.PeriodicTask`。 |
| `tests/services/test_scheduled_task_beat_scheduler_service.py` | 新增 SQLite 隔离测试，覆盖创建、空基线回填和午夜重载保持 due。 | 固定 Beat 基线不可被同步覆盖的契约。 |
| `.gitignore` | 放行该定时任务调度器测试文件。 | 确保回归测试被版本控制。 |

## 3. 同步流程与关键字段

```text
ScheduledTask（业务任务表）
  -> 过滤 IsDeleted=0、IsEnabled=1、EffectiveDate <= now < ExpiryDate
  -> 稳定名称 scheduled_task_<TaskID.hex()>
  -> 解析/复用 CrontabSchedule（Asia/Shanghai）
  -> 新建或更新 PeriodicTask
       ├─ 新记录：last_run_at = now
       └─ 已有记录：仅 last_run_at is NULL 时回填 now
  -> 非活动 Beat 记录 enabled = false
  -> 单事务提交
```

同步器使用独立同步 SQLAlchemy Engine、`NullPool` 和同步 `Session`，完成后释放 Engine；异步业务服务通过 `asyncio.to_thread()` 调用它，避免阻塞事件循环。

关键约定：

- `PeriodicTask.name` 由业务任务 UUID 生成，不能使用任务名称；任务改名仍应更新同一 Beat 记录。
- `PeriodicTask.task` 固定为 `app.tasks.scheduled_task_tasks.dispatch_scheduled_task`，Beat 只负责派发统一入口。
- `args` 固定为 `[task_id_hex, "cron"]`，执行器再从业务表读取最新配置。
- `CrontabSchedule` 按五段 Cron 字段和 `Asia/Shanghai` 时区复用，避免重复表行。
- 本次同步统计返回活动任务数量：`{"synced": <count>}`；禁用旧记录不计入 `synced`。

## 4. `last_run_at` 基线规则

### 4.1 新建任务

业务任务首次进入活动集合时，创建的 `PeriodicTask` 写入：

```python
last_run_at = now
```

这为 Celery Beat 提供明确的持久化基线，不让调度器把一个刚创建的任务当成从未运行过的历史任务而立即补发多次。

### 4.2 已有任务

已有 `PeriodicTask` 更新 Cron、参数、描述和启用状态时：

```python
if periodic_task.last_run_at is None:
    periodic_task.last_run_at = now
```

非空值必须保持不变。`last_run_at` 是 Beat 的运行事实，不是业务配置同步字段；每次全量同步写入 `now` 会掩盖任务是否到期，也会让重载时间影响调度行为。

### 4.3 午夜重载

测试用例先在 `2026-07-14 16:40` 同步任务，再在 `2026-07-15 00:00` 重载配置。断言第二次同步后：

- `last_run_at` 仍为首次同步时间；
- `total_run_count` 未被同步器修改；
- Cron 在午夜仍按原时间基线判断为 due。

这条规则适用于任何会在午夜、配置变更或进程启动时执行的 Beat 全量同步器。

## 5. 与运行时执行器的边界

该提交只修复 Beat 元数据同步，不改变 `dispatch_scheduled_task` 的执行槽、业务状态机或邮件发送逻辑：

- Beat 记录的 `last_run_at` 不等于业务执行成功时间；
- 业务执行仍需在 `dispatch_task`/Worker 层创建执行记录并做幂等领取；
- Celery task id、业务 `trace_id` 和执行日志应分别保存，不能用 `last_run_at` 充当业务审计时间；
- Beat 调度表与业务任务表不是同一事务，Beat 同步失败要有日志、告警或下一轮补偿。

## 6. 迁移到其它项目

1. 为每个业务任务定义稳定的 Beat 名称、统一派发任务和参数格式。
2. 全量同步时只纳入当前生效任务，明确结束时间的开闭区间（本实现为 `EffectiveDate <= now < ExpiryDate`）。
3. 新建 `PeriodicTask` 时设置 `last_run_at=now`；已有非空值绝不覆盖，仅对历史空值做一次回填。
4. Cron 表按表达式和时区唯一复用，并在后端校验表达式，不依赖前端输入。
5. 不活动任务只禁用，不删除，保留历史执行关联；重新激活时复用原 Beat 名称。
6. 让同步事务一次性提交；失败回滚并释放连接，下一轮可安全重试。
7. 在目标数据库和 Celery Beat 版本上验证 `last_run_at` 的时区类型、序列化和 `schedule.is_due()` 语义。

## 7. 验收清单

- [ ] 新活动任务创建的 `PeriodicTask.last_run_at` 等于同步时刻。
- [ ] 已有非空 `last_run_at` 在重复同步、配置更新和午夜重载后保持不变。
- [ ] 历史空 `last_run_at` 只被回填一次，不覆盖之后 Beat 写入的时间。
- [ ] Beat 名称、统一任务名、Cron 参数和时区可重复同步。
- [ ] 过期、禁用和删除的业务任务对应 Beat 记录被禁用而非误派发。
- [ ] 同步异常不会留下半写入状态，Engine/Session 始终释放。
- [ ] 业务执行器仍独立负责执行槽、幂等、超时和通知历史。
- [ ] 测试覆盖创建、空值回填、午夜重载及 `schedule.is_due()`。

## 8. CodeGraph 与 Git 复核命令

```bash
rtk codegraph explore "ScheduledTaskBeatSchedulerService sync_all_scheduled_tasks_beat_sync _get_or_create_crontab"
rtk codegraph explore "ScheduledTaskService _sync_beat_tasks_async dispatch_scheduled_task"
rtk codegraph node backend/JSECommon/app/services/scheduled_task/beat_scheduler_service.py
rtk codegraph node backend/JSECommon/app/services/scheduled_task/task_service.py
rtk git -C backend/JSECommon show --stat --summary --format=fuller a3b3ddff
rtk git -C backend/JSECommon show --name-status --format= a3b3ddff
rtk git -C backend/JSECommon show a3b3ddff -- app/services/scheduled_task/beat_scheduler_service.py tests/services/test_scheduled_task_beat_scheduler_service.py
```
