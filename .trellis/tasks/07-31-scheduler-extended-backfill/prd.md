# 定时任务扩展历史补发

## Goal

为未来具备可重放业务语义的定时任务，将单时点历史补发窗口从 90 天扩大到 365 天；保持 Cron
匹配、审计、活动运行冲突、快照、共享投递路径和任务自身幂等约束。

## Confirmed Facts

- 来源为已归档父任务 `07-26-scheduled-task-management` 的 D-003；当前
  `POST /scheduler/jobs/{job_id}/backfill` 接受一个带时区的 `planned_at`，只允许过去 90 天内且
  精确命中 Cron 的时点。
- D-001 已在前序 scheduler operation-capability 工作中落地：`ScheduledTask` 的
  `allow_backfill` 静态值经 `task_capabilities(class_path=...)` 解析，公开 job 响应以
  `can_backfill` 供页面隐藏不可用操作；默认拒绝，只有实现类显式声明 `True` 才能获得补发
  能力，服务端仍是最终强制边界。
- 当前两个生产 inventory 定时任务均显式 `allow_backfill = False`，因为它们不按
  `ScheduledTaskContext.planned_at` 重放业务含义。当前任务不得擅自改变这项语义。
- 路由和服务继续使用 `scheduler.jobs.manage`，创建带请求人的 `MANUAL_BACKFILL` run；
  `create_run()` 锁定 job，并拒绝已有 `QUEUED`/`RUNNING` run 的任务。现有服务按时间、Cron、
  能力顺序校验，并在任何 `create_run()` 调用前拒绝失败请求。
- 运行快照保留 90 天，cleanup 只删除终态 run；任务类仍须在其持久化边界保证幂等。

## Confirmed Product Decision

- **D003-001 - 面向未来的可重放任务**：365 天窗口只适用于未来显式声明
  `allow_backfill = True` 且能定义 `ScheduledTaskContext.planned_at` 历史业务含义的实现类。
  D-003 不改变任何现有 inventory 任务的静态能力，也不为它们补造历史重放语义。
- `allow_backfill = True` 是实现者对可重放语义和幂等边界的静态承诺，不是管理员可在 job 配置、
  API 请求或 UI 中开启的开关。D-003 只消费既有 `task_capabilities()`，不维护第二份白名单。

## Requirements

- **D003-R1 历史边界**：允许严格早于服务端当前 UTC 时刻、且相差不超过 365 个 24 小时的单个
  时点（精确 365 天包含在内）；未来、当前、超过 365 天、
  无时区的输入必须拒绝。日期范围、批量和多时点请求不提供 API 或 UI 入口。
- **D003-R2 Cron 约束**：所有允许的 `planned_at` 仍须按既有上海时区规则精确匹配 job 的五字段
  Cron 表达式。
- **D003-R3 能力依赖**：365 天补发只适用于 D003-001 所述、D-001 静态声明为允许补发的未来
  `ScheduledTask` 实现类。服务端必须复用 D-001 的能力契约，不得新增数据库、JSON 配置或客户
  端可修改的第二套白名单，也不得把现有 `False` 改为 `True`。
- **D003-R4 授权和副作用**：继续由 `scheduler.jobs.manage` 保护；权限或实现类能力检查失败时，
  不创建 `SchedulerRun`、不发送 Celery 消息、不改变既有运行状态。
- **D003-R5 运行契约**：成功请求每次最多创建一个 `QUEUED` 的 `MANUAL_BACKFILL` run，并冻结
  当前 class path、配置快照和请求人；既有活动 run 冲突、审计归属、错误摘要和租约/投递规则保持
  不变。
- **D003-R6 容量边界**：API 和服务层不得引入循环创建或直接投递；新 run 必须进入现有
  `next_dispatch_at`/租约/批量上限为 100 的共享扫描路径，避免消息风暴。
- **D003-R7 管理体验**：管理页沿用现有单时点补发 modal，明确显示上海时区、365 天范围、命中
  Cron 和一次只创建一个 run 的业务副作用提示；D-001 能力禁止时继续不提供可执行的补发动作。
  浏览器校验只能辅助提示，服务端是最终边界。

## Acceptance Criteria

- [x] 365 天边界内的带时区、命中 Cron、且由 D-001 允许补发的未来实现类请求返回
      `MANUAL_BACKFILL`，并
      持久化请求人、UTC `planned_at` 和 class/config 快照。
- [x] 超过 365 天、未来/当前、无时区或未命中 Cron 的请求返回安全的 4xx 错误且数据库无新增
      run、无审计写入和无消息投递副作用。
- [x] 没有 `scheduler.jobs.manage` 的调用者不能执行补发；拥有该权限但实现类未声明允许补发
      时同样被拒绝且无副作用。
- [x] 已存在活动 run 时返回既有冲突错误；原活动 run 和其他任务的状态保持不变。
- [x] 单次成功请求只新增一个 run；run 由既有 dispatch lease、100 条批量上限和 at-least-once
      Celery 路径处理，服务不增加绕过这些边界的直投递。
- [x] 管理页展示 365 天上海本地时间边界和风险确认，且不出现日期范围或批量控件。
- [x] 自动化测试覆盖长期历史、上海时区、Cron 匹配、D-001 能力矩阵、RBAC、活动冲突、快照、
      容量和失败副作用。
- [x] 两个现有 inventory 任务继续返回 `can_backfill=false`，不因 D-003 出现补发入口或获得历史
      重放语义。

## Out of Scope

- 改变业务数据保留政策、运行快照清理期限、任务自身幂等实现、自动调度/租约语义，或替代专用
  数据修复流程。
- 日期范围、批量/多时点回放、新权限、新审批流、数据库/配置白名单和新的队列或 Celery 路由。

## Dependency And Sequencing

- D-001 已定义并落地静态实现类能力契约；D-003 的服务检查和前端可用性展示只消费
  `task_capabilities()` 和 `can_backfill`。
- D-003 不等待新生产任务加入。未来任务只有在其实现者先声明可重放语义和 `allow_backfill=True`
  后，才自动获得 365 天的单时点平台边界。
