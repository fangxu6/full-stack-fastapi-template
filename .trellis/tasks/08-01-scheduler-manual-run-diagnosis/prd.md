# 排查定时任务手工执行未真正运行

## Goal

诊断用户手工执行日报创建与投递重试任务后，为什么没有观察到预期日报或邮件副作用，并以持久化运行、队列投递和 worker 日志确定发生位置。

## Confirmed Facts

- 管理页的“立即执行”只创建一条 `MANUAL_NOW`、`QUEUED` 的 `SchedulerRun`；共享
  dispatcher 随后向 Celery 投递该 run ID，worker 才调用任务实现。
- `InventoryDailyReportRetryTask.run()` 不创建日报。它只查询当前到期的
  `InventoryDailyReportDelivery`，再逐条投递邮件 worker；没有待处理 delivery 时会正常
  返回且不会产生邮件副作用。
- 本机 PM2 当前显示 backend、Celery beat 和 Celery worker 均为 `online`。这不是已证明
  的执行成功，只排除了进程未启动这一项初步假设。
- 诊断必须以用户实际手工触发产生的 `SchedulerRun`、关联日报 delivery 行和进程日志为准，不能
  用测试数据库或仅凭页面状态推断。
- 日报创建 job 的三条近期 `MANUAL_NOW` run（`id=3`、`id=5`、`id=6`）均被 worker 执行，
  但运行在 `17:20–17:28 +08:00`，因此均为 `SKIPPED`，分类为
  `DAILY_REPORT_WINDOW_EXPIRED`，没有产生日报。其 cron 仍为每日上海时间 `08:00`。

## Requirements

- R1：识别日报创建与投递重试两类 `MANUAL_NOW` run 的状态、尝试次数、错误分类、计划/开始/结束时间和
  `next_dispatch_at`。
- R2：核对该 run 是否被 scheduler dispatcher 投递、worker 是否接收并执行，以及失败时的日志证据。
- R3：核对执行时是否存在日报与到期的日报 delivery；区分“任务未执行”“窗口外跳过”与“已执行但无到期工作”。
- R4：在没有可信根因前不修改生产代码、调度定义或业务数据。

## Acceptance Criteria

- [x] 给出一条可复核的因果链，定位为运行未创建、未投递、worker 未执行、执行失败，或无到期业务
      工作中的一种，并附带时间/状态/日志证据。
- [x] 明确日报创建与投递重试任务的实际业务语义，以及用户若要生成或重试时应满足的持久化前提。
- [x] 若发现产品或实现缺陷，单独列出最小修复方案与验证步骤；本诊断未发现需要修复的调度缺陷。

## Observed Evidence

- 实际 job 为 `id=2`、`Inventory daily report delivery retry`，处于启用状态。
- 它在 `2026-08-01 17:19:10+08:00` 和 `17:21:11+08:00` 创建的两条
  `MANUAL_NOW` run（分别为 `id=2`、`id=4`）都在下一个扫描分钟启动，均为
  `SUCCEEDED`，`attempt_count=1`，无错误分类或摘要，且投递字段已清空。
- 同一 job 在 `17:15:00+08:00` 的正常调度 run 也为 `SUCCEEDED`。
- 查询应用数据库没有返回任何 `InventoryDailyReport` 或
  `InventoryDailyReportDelivery` 行；因此 retry 查询不到到期的 delivery ID，不会投递邮件
  worker，也不会产生业务可见副作用。
- PM2 显示 backend、Celery beat 和 Celery worker 均为 `online`；worker 的 PM2 文件日志
  没有额外输出，持久化 run 状态是本次执行成功的主证据。

## Diagnosis

根因是**没有可重试的日报 delivery**，而不是手工任务未执行。

`InventoryDailyReportRetryTask` 的职责仅为发现状态为 `PENDING` 或 `RETRY_WAIT` 且
`next_attempt_at` 已到期的既有 delivery，并将其交给邮件 worker。它不生成日报、不创建
delivery，也不强制发送邮件；在空表上成功返回是预期行为。

若要产生可重试的邮件，必须先存在日报与收件人解析结果，继而有待处理或重试等待的 delivery。
日报创建任务只在上海时间 `08:00` 至 `08:15` 的业务窗口生成前一日快照；窗口外手工运行会被
跳过，不能用 retry 任务替代日报生成或历史补发。

日报创建任务未生成日报的原因也已确认：它在 worker 实际开始执行时调用
`report_date_for_scheduled_run(context.started_at)`，仅在上海时间 `[08:00, 08:15)` 返回业务日期。
用户在 `17:19–17:27 +08:00` 发起的手工运行都在下一扫描分钟开始，落在窗口外，因而按设计记录
`DAILY_REPORT_WINDOW_EXPIRED` 并跳过。它没有失败，也不会补造任意历史日报。

## Out Of Scope

- 修改日报生成、收件人配置、SMTP、Celery 重试策略或手工运行交互，除非诊断完成后用户另行授权。
