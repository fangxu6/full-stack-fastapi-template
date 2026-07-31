# 定时任务人工操作能力设计

## Scope And Boundaries

本任务为既有 scheduler 模块增加最小的静态实现类契约。它只决定管理员是否可以创建新的
`MANUAL_NOW` 或 `MANUAL_BACKFILL` run；不改变自动扫描、已持久化 run、Cron、调度租约、Celery
投递、审计 actor、RBAC 或数据库结构。

没有新增存储模型、迁移、权限或独立能力 API。能力只从允许的 Python class path 解析，不能被
`SchedulerJob.config`、`SchedulerRun.config` 或 HTTP 输入修改。

## Static Contract

`ScheduledTask` 声明以下带兼容默认值的类变量：

```python
allow_run_now: ClassVar[bool] = True
allow_backfill: ClassVar[bool] = True
```

这不是新值对象或配置层。新实现类继承两个 `True` 默认值；仅当它无法正确处理某个人工触发语义
时，覆写对应值为 `False`。

当前库存日报创建和投递重试任务都显式设置 `allow_backfill = False`。两者的业务代码均不消费
`ScheduledTaskContext.planned_at`，其中创建任务还只在上海时间日报窗口内运行；因此把一个历史
时点标记为补发不会重放该时点的业务事实。两个任务继续继承 `allow_run_now = True`。

## Data And Error Flow

```text
SchedulerJob.class_path
  -> resolve_task_class()
  -> ScheduledTask allow_* class variables
  -> service run_now()/backfill() check before create_run()
  -> SchedulerValidationError (422, detail + request_id) or SchedulerRun

SchedulerJob.class_path
  -> same resolver and capability helper
  -> SchedulerJobPublic.can_run_now / can_backfill
  -> generated OpenAPI client
  -> SchedulerJobsPage action visibility
```

`service.py` owns one typed helper that resolves the allowed task class once and returns the two booleans. The
helper is used both by API serialization and manual-run creation, so the UI hint and server enforcement cannot
drift. `run_now()` and `backfill()` load the active job, read the matching boolean, and reject before
`create_run()` when it is false. The expected rejection uses the existing `SchedulerValidationError` 422 path
with a stable operation-specific detail; FastAPI's global handler preserves `detail` and `request_id`.

Allowed operations retain the existing `create_run()` transaction: it locks the job, detects active runs, freezes
class/config, records `requested_by`, and leaves dispatch to the bounded lease-based scanner. Rejected operations
must not create a run, change job state, write audit data, or call a Celery publisher.

## API And UI Contract

`SchedulerJobPublic` receives two required read-only booleans: `can_run_now` and `can_backfill`. Every existing
job response (list, get, create, update, enable, disable, restore) is built through the existing router helper,
so all return the same current capability values. No request DTO changes.

The generated client is regenerated from OpenAPI. `SchedulerJobsPage` continues using its existing query and
mutation structure. When the user has `scheduler.jobs.manage`, it renders the immediate-run button only when
`can_run_now` is true and the backfill button only when `can_backfill` is true. It does not add explanatory
dialogs, extra confirmations, new screens, or client-side authorization. Read-only users retain history-only
access.

## Compatibility, Rollback, And Risks

- Existing or future classes without overrides remain fully manually operable, matching the previous global
  behavior.
- The two known daily-report class paths lose only the misleading historical-backfill entry. Immediate execution
  and automatic schedules are unchanged.
- Because capability is evaluated only before new manual run creation, existing queued/running/historical runs
  remain executable and readable after deployment.
- Rollback is application-code-only: remove the two public fields and checks, regenerate the client, and restore
  the two buttons. No data migration or persisted state rollback exists.
- A class path that has become invalid still follows existing scheduler validation behavior; this task must not
  convert it into a permissive capability result.

## Spec And Wiki Impact

No `.trellis/spec` or `docs/llm-wiki` update is planned. This is a bounded follow-up of the documented scheduler
runtime; it introduces no reusable cross-module convention beyond the local `ScheduledTask` interface.
