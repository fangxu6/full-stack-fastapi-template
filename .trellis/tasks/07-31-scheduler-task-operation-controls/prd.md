# 定时任务实现类操作限制

## Goal

为每个已部署的 `ScheduledTask` 实现类声明是否允许人工立即运行和单时点历史补发，避免仅凭
全局 `scheduler.jobs.manage` 权限对所有实现类开放高风险操作。

## Confirmed Baseline

- 来源为已归档父任务 `07-26-scheduled-task-management` 的 D-001；首期默认所有实现类均支持
  立即运行和 90 天内的单时点补发。
- 当前 API 的 `/scheduler/jobs/{job_id}/run-now` 与 `/backfill` 均只检查
  `scheduler.jobs.manage`；服务层用任务定义冻结的 class path 创建 run。
- 已部署 class path 必须位于 `app.modules.<business_module>.scheduled_tasks.<Class>`，并继承
  `ScheduledTask`；任务配置由实现类的 `config_model` 约束。

## Requirements

- 操作能力必须由已部署实现类的静态、可审查元数据声明，不能由数据库 JSON 或客户端输入扩大。
- 后端在创建 `MANUAL_NOW` 或 `MANUAL_BACKFILL` run 前强制检查能力；前端仅作为辅助提示，
  不能替代服务端授权。
- 自动调度、运行租约、冻结快照、现有 `scheduler.jobs.read/manage` 权限及 90 天补发上限保持
  不变，除非 D-003 另行变更该上限。
- 新增或变更实现类必须有明确的兼容性策略，避免无意中改变现有库存日报任务的人工操作能力。

## Acceptance Criteria

- [ ] 每个实现类可独立声明立即运行和历史补发是否允许，且声明值不来自可持久化配置。
- [ ] 禁止的操作在 API 和服务层均被拒绝，不创建 `SchedulerRun`、不投递 Celery 消息。
- [ ] 管理页准确反映当前实现类能力，且保留通用 RBAC 对读写操作的控制。
- [ ] 自动运行和允许的人工操作继续满足现有冻结快照、活动 run 冲突和审计归属契约。
- [ ] 覆盖允许/禁止矩阵、现有实现类兼容性、API 副作用和前端操作状态的自动化测试。

## Out of Scope

- 新增实现类、动态脚本执行、按数据库任务定义覆盖实现类能力，或修改 D-003 负责的补发时限。

## Open Question

- 需确定能力的默认策略，以及现有库存日报创建和投递实现类的立即运行/补发允许矩阵。
