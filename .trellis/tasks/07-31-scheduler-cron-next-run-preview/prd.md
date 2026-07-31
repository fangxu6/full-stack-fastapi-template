# 定时任务 Cron 后续时点预览

## Goal

提供只读的 Cron 后续执行时点预览，使管理员能在保存或查看任务定义时理解其 `Asia/Shanghai`
调度含义，而不影响任何 job、run 或 Celery 投递状态。

## Confirmed Baseline

- 来源为已归档父任务 `07-26-scheduled-task-management` 的 D-002；当前仅服务端校验 Cron 并保存
  `SchedulerJob.next_run_at`。
- `parse_cron()` 仅接受五段 Celery Cron；`next_run_at()` 已按 `Asia/Shanghai` 计算并以 UTC 返回。
- 管理 API 已有 read/manage 权限模型，前端管理页已有 Cron 编辑和任务读取能力。

## Requirements

- 预览必须复用现有 Cron 解析与时区语义，不能引入第二套 Cron 解释器或改写 scheduler state。
- API 必须只读、受 scheduler read 权限保护，并明确返回基准时间之后的有序时点及其时区表示。
- 无效 Cron、无时区基准时间或超出服务端上限的请求必须遵循统一错误契约，且不能写入数据库。
- 管理页应在合适位置显示预览，清晰区分服务器保存的 `next_run_at` 和假设基准时间计算的结果。

## Acceptance Criteria

- [ ] 对五段 Cron 预览出的时点与生产调度器的上海时区、日/周 AND 语义一致。
- [ ] 预览请求不创建或修改 job/run，不触发 Celery，也不暴露调度器内部 dispatch lease 字段。
- [ ] API 对无 read 权限、非法 Cron、非法基准时间和超限数量返回可预测错误。
- [ ] 前端正确显示上海本地时间，且编辑未保存的 Cron 可与已保存任务区分。
- [ ] 覆盖跨日/月、日周组合、时区转换和只读副作用的后端/API/前端测试。

## Out of Scope

- 多 Cron 计划、自动修复 Cron、修改当前任务的执行计划，或按预览批量创建补发 run。

## Open Question

- 需确定每次预览的时点数量上限，以及是否允许为未保存的 Cron 提交独立预览请求。
