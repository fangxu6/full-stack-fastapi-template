# 定时任务 Cron 后续时点预览

## Goal

提供只读的 Cron 后续执行时点预览，使管理员能在保存或查看任务定义时理解其 `Asia/Shanghai`
调度含义，而不影响任何 job、run 或 Celery 投递状态。

## Confirmed Facts

- 本任务承接已归档父任务 `07-26-scheduled-task-management` 的延期项 D-002。父任务固定五段
  Celery Cron、`Asia/Shanghai` 解释、日与周同时受限时采用 AND 语义，并将 `next_run_at`
  以 UTC 存储。
- `backend/app/modules/scheduler/cron.py` 已是上述语义的唯一实现：`parse_cron()` 仅接受五段
  Cron，`next_run_at()` 要求时区感知基准时间、转换为上海时区计算并返回 UTC。预览必须在此
  基础上迭代，不能引入另一套 Cron 解释器或依赖。
- 当前 `backend/app/modules/scheduler/router.py` 的 scheduler 路由以 `scheduler.jobs.read`
  保护只读操作；任务写入和人工运行均由独立服务路径拥有。
- 当前管理页 `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx` 已包含 Cron 编辑输入、
  已保存任务的 `next_run_at` 展示和只读权限判断，但尚无预览请求或结果视图。
- 新增公开 FastAPI schema 会更新 OpenAPI；实施时必须通过 `scripts/generate-client.sh` 刷新
  `frontend/src/client/**`，不能手工改生成文件。

## Requirements

1. 预览必须复用现有 Cron 解析、上海时区和严格后续时点语义；输出按时间升序，且每个时点
   都晚于所采用的基准时刻。
2. API 必须只读、受 `scheduler.jobs.read` 权限保护；不得读取或暴露 dispatch lease 等内部字段，
   也不得创建/更新 `SchedulerJob`、`SchedulerRun`、审计字段或 Celery 消息。
3. API 响应必须明确使用的基准时间和 `Asia/Shanghai` 时区；时点仍以时区感知 UTC ISO 值承载，
   前端将其格式化为上海本地时间，不能将 UTC 文本直接作为本地时间显示。
4. 无效 Cron 必须在任何持久化副作用之前返回统一 `422` 错误（`detail` 与 `request_id`）。
   API 不接受基准时间或数量参数；无权限用户维持现有 `403` 契约。
5. 管理页必须把服务器保存的 `next_run_at` 与“基于当前表单 Cron 的预览结果”明确区分；请求
   失败时沿用既有 API 错误反馈，不以客户端 Cron 解析替代服务端结果。

## Confirmed Product Decision

- **D-001 - 直接预览编辑中的 Cron**：提供无状态的表达式预览 API，直接接收 Cron；已保存
  任务和编辑中尚未保存的 Cron 复用同一能力。该 API 不接受任务 ID、实现类或配置，因此不读取
  任务状态，也不具备改变调度状态的路径。
- **D-002 - 固定预览窗口**：API 不接受基准时间或数量。服务端以收到请求时的当前 UTC 时间作为
  基准，固定返回严格晚于该基准的 5 个时点，并在响应中回显该基准和 `Asia/Shanghai` 时区。
  实施内部 helper 可以接收测试时钟，但这不是公开 API 参数。
- **D-003 - 编辑时自动刷新**：编辑页的非空 Cron 输入变化后自动请求预览；结果只代表当前表单
  值，不能与已保存任务的 `next_run_at` 混用。预览不改变表单、不会保存任务，也不阻断管理员
  继续编辑或提交。
- **D-004 - 内联反馈**：Cron 输入停止变化约 300ms 后发起预览。无效或未完成的表达式在预览区域
  内显示当前服务端错误，不弹出全局提示；旧 Cron 的结果与错误必须在输入变化时消失。预览失败
  不阻断保存，保存仍由既有服务端定义校验决定。

## Acceptance Criteria

- [x] 五段 Cron 的预览结果与生产调度器一致，包括跨日/月、上海与 UTC 转换及日/周 AND 语义；
  响应精确包含五项、有序且严格晚于响应声明的基准时间。
- [x] 预览 API 仅需 `scheduler.jobs.read`，并且在成功、422、403 路径都不创建或修改 job/run、
  审计数据或 Celery 消息。
- [x] 无效 Cron 稳定返回统一 `422` 错误契约；无权限请求维持 `403`，两种路径都不产生持久化
  副作用。
- [x] 管理页以上海本地时间呈现预览，明确区分已保存的 `next_run_at` 和编辑中 Cron 的计算结果，
  并显示服务端错误反馈。
- [x] 后端单元/API、生成客户端与浏览器测试覆盖成功、权限、无效输入、时区和只读副作用。

## Out of Scope

- 多 Cron 计划、自动修复 Cron、客户端自行解释 Cron、改变任务当前计划或更新 `next_run_at`。
- 通过预览创建运行、批量补发、增加新的调度权限、数据库字段、配置开关或新的后台任务。
- 用预览替换单时点补发的匹配校验，或暴露内部 dispatch lease 状态。
