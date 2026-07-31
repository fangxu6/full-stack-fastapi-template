# 定时任务实现类操作限制

## Goal

为 `ScheduledTask` 提供极简的静态人工操作能力声明，使确实不能正确处理某种人工触发方式的
实现类可禁用该入口，同时保持企业内部管理系统的默认可用体验。

## Confirmed Baseline

- 来源为已归档父任务 `07-26-scheduled-task-management` 的 D-001；首期默认所有实现类均支持
  立即运行和 90 天内的单时点补发。
- 当前 API 的 `/scheduler/jobs/{job_id}/run-now` 与 `/backfill` 均只检查
  `scheduler.jobs.manage`；服务层用任务定义冻结的 class path 创建 run。
- 已部署 class path 必须位于 `app.modules.<business_module>.scheduled_tasks.<Class>`，并继承
  `ScheduledTask`；任务配置由实现类的 `config_model` 约束。
- 当前仅部署两个库存日报实现类：`InventoryDailyReportCreateTask` 和
  `InventoryDailyReportRetryTask`。两者都不消费 `ScheduledTaskContext.planned_at`；前者只会在
  上海时间 08:00-08:10 为“昨日”创建报表，后者只扫描当前待投递的日报。因此当前的
  `MANUAL_BACKFILL` 不会按请求的历史时点执行相应业务，不能作为可支持的补发能力。

## Requirements

- 操作能力必须由实现类的静态类属性声明，不能由数据库 JSON 或客户端输入改变。为兼容当前
  内部管理行为，两个属性均默认允许；只有实现类明确覆写为 `False` 才关闭对应操作。
- 后端在创建 `MANUAL_NOW` 或 `MANUAL_BACKFILL` run 前检查能力；前端只据此隐藏或禁用不可用
  操作，不能替代服务端检查。
- 自动调度、运行租约、冻结快照、现有 `scheduler.jobs.read/manage` 权限及 90 天补发上限保持
  不变，除非 D-003 另行变更该上限。
- 新增或变更实现类继承“立即运行”和“历史补发”均允许的默认值；只在业务语义无法正确支持
  该操作时覆写对应布尔值。这两个值不进入 job/run JSON 快照，因而不能由 API、数据库配置或
  历史 run 改变。
- 能力契约只使用 `ScheduledTask` 上的两个 `ClassVar[bool]`，不增加值对象、数据库字段、
  新权限、审批流或配置白名单。

## Acceptance Criteria

- [x] 每个实现类可通过两个静态布尔值独立覆写立即运行和历史补发是否允许，且值不来自
      可持久化配置。
- [x] 禁止的操作在 API 和服务层均被拒绝，不创建 `SchedulerRun`、不投递 Celery 消息。
- [x] 管理页准确反映当前实现类能力，且保留通用 RBAC 对读写操作的控制。
- [x] 自动运行和允许的人工操作继续满足现有冻结快照、活动 run 冲突和审计归属契约。
- [x] 覆盖默认允许、显式禁止、现有库存日报兼容性、API 无副作用和前端操作状态的自动化测试。

## Out of Scope

- 新增实现类、动态脚本执行、按数据库任务定义覆盖实现类能力，或修改 D-003 负责的补发时限。

## Capability Contract

```python
class ScheduledTask:
    allow_run_now: ClassVar[bool] = True
    allow_backfill: ClassVar[bool] = True
```

- 默认值保持首期“所有实现类均可人工操作”的兼容性，不要求每个新增实现类重复声明。
- `InventoryDailyReportCreateTask` 与 `InventoryDailyReportRetryTask` 保留默认的
  `allow_run_now = True`，并显式声明 `allow_backfill = False`：两者均不消费 `planned_at`，
  故不能正确执行指定历史时点的补发。
- 服务端用将被冻结到新 run 的 job class path 解析当前实现类后读取该静态值；禁用时在创建 run 之前返回
  既有统一 4xx 错误。API 返回只读的 `can_run_now` 与 `can_backfill`，管理页据此不提供相应
  操作。不会新建独立能力 API、表、迁移或权限。
