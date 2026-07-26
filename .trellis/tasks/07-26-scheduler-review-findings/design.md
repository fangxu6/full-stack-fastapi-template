# 定时任务管理审查问题修复设计

## Scope and invariants

本设计只修复审查确认的问题。以下父任务约束不变：

- PostgreSQL 是定义和运行记录的事实来源；Redis 只是 Celery broker/result backend。
- Beat 仍每分钟扫描，所有消息仍进入默认队列，Worker 仍单并发。
- 运行仍采用至少一次语义，业务实现负责自身幂等，通用运行器不重试业务失败。
- HTTP API 可以在告警邮件配置缺失时启动。

## 1. Recipient parsing and startup validation

`SchedulerSettings.SCHEDULED_TASK_ALERT_RECIPIENTS` 保留 `list[EmailStr]` 类型和现有
`BeforeValidator`。在字段 `Annotated` 中加入已安装的 `pydantic_settings.NoDecode`，阻止
Settings source 在业务 validator 前按 JSON 解析逗号字符串。这样环境变量和 `.env` 都进入
同一个 CSV parser，不增加备用格式或依赖。

Celery 的 `Signal.send()` 会捕获接收器异常，因此移除 `worker_init`/`beat_init` 校验。改为在
`app.core.celery` 模块加载、创建 Celery app 前直接调用
`validate_scheduler_runtime_settings()`：

- Worker/Beat 的 `-A app.core.celery:celery_app` 导入失败并非零退出。
- FastAPI 路由继续延迟导入 Celery，因此 HTTP 启动不执行该校验。
- `local` 仍直接通过；非本地缺 SMTP 或收件人抛出安全、无凭据的配置错误。

## 2. Credential validation

凭据检查继续集中在 scheduler service 的保存/快照边界，不让各实现类重复实现。

1. 扩展规范化键名 denylist，至少覆盖 `password`、`token`、`secret`、`credential`、
   `authorization`、`api_key`、`access_key`、`private_key`、`dsn`、`connection_string` 及
   下划线/连字符变体。
2. 递归遍历 `config_model.model_json_schema()`，发现 Secret 类型生成的
   `format: password` 即拒绝整个实现类。JSON Schema 已包含嵌套模型、容器、union 和 `$defs`，
   无需维护第二套 Python typing 解析器。
3. 对提交配置和 `model_dump(mode="json")` 后的快照继续递归检查所有对象键。

检查发生在写入 `scheduler_job.config`、创建 `scheduler_run.config` 和返回 task schema 之前。
不扫描普通字符串内容，避免把合法非凭据业务文本误判为秘密。

## 3. Bounded dispatch

在 `scheduler_run` 增加可空 UTC 字段 `next_dispatch_at`，并为
`status = 'QUEUED'` 的到期查询增加部分索引。新运行以创建时间作为首次投递时间。

共享投递 helper 按以下步骤工作：

1. 选取 `QUEUED AND next_dispatch_at <= now` 的运行，按创建时间排序，单次最多 100 条，并用
   `FOR UPDATE SKIP LOCKED` 领取。
2. 在发送前把 `next_dispatch_at` 推进到
   `now + CELERY_VISIBILITY_TIMEOUT_SECONDS` 并提交，避免并发扫描或下一分钟重复领取。
3. 逐条向默认队列发送 `scheduler.execute_run(run_id)`；broker 明确失败时，将该运行的
   `next_dispatch_at` 调整到下一扫描分钟。
4. Worker 领取后状态变为 `RUNNING`，自然退出待投递查询。若消息在 broker 接受后丢失或发送
   边界崩溃，仍为 `QUEUED` 的记录会在 visibility timeout 后再次投递。

扫描器不再查询并发送全部 `QUEUED` ID。自动扫描提交运行后调用该 helper；人工 API 创建运行
后也按 run ID 调用同一 helper 立即尝试，Beat 作为持久化兜底。发送边界仍允许重复，但每个
运行最多按 visibility timeout 重投一次，不会形成每分钟消息风暴。

## 4. Run creation concurrency

所有 `create_run` 路径先锁定对应 `scheduler_job` 行，再检查活动运行并插入。自动扫描、立即
运行和补发因此在同一个定义上串行化；`uq_scheduler_run_job_active` 继续作为数据库兜底。

批量扫描中的非提交插入放在当前任务定义的 savepoint 内。唯一约束冲突只回滚该 savepoint，
转换为 `ConflictError`；`create_run(commit=False)` 禁止调用外层 `session.rollback()`。扫描器可
按既有重叠逻辑记录该任务为跳过，并继续提交其他定义及其 `next_run_at`。

## 5. Execution failure boundary

执行器拆成两个明确阶段：

1. 解析冻结类路径并校验冻结配置。此阶段的 `ValueError`/Pydantic validation error 映射为
   `CONFIGURATION_INVALID`。
2. 调用已经构造好的 `task.run()`。只单独捕获 `ScheduledTaskSkipped`；其余异常，包括
   `ValueError`，统一映射为 `EXECUTION_FAILED`。

数据库终态、错误摘要和告警种类继续使用现有安全文本，不保存 traceback 或异常原文。

## 6. Shanghai datetime-local value

在 scheduler 页面旁增加一个纯函数，将 `Date` 加上固定 UTC+8 偏移后格式化为
`YYYY-MM-DDTHH:mm`，用于 `datetime-local.max`。上海在本任务 90 天补发窗口内没有夏令时，
无需引入日期库。提交函数继续为输入追加 `+08:00` 后调用 `toISOString()`。

纯函数测试固定 UTC 输入，断言上海本地最大值和提交 UTC 值；不依赖测试机器时区。

## Migration and compatibility

- 新 Alembic revision 只增加 `scheduler_run.next_dispatch_at` 和对应部分索引。
- 升级时把现有 `QUEUED` 行的 `next_dispatch_at` 回填为 `created_at`，其他状态保持 `NULL`；新列
  最终保持 nullable，因为终态和运行中记录不需要投递时间。
- 降级先删除索引再删除列。模型、迁移和测试清理顺序仍为 run 后 job。
- API public schema不公开 `next_dispatch_at`，无需重新生成前端 client。

## Evidence mapping

| Finding | Current location | Design section |
| --- | --- | --- |
| CSV 被 Settings JSON 预解析 | `backend/app/modules/scheduler/config.py` | 1 |
| Celery signal 异常不阻止启动 | `backend/app/core/celery.py` | 1 |
| 凭据字段可绕过 | `backend/app/modules/scheduler/service.py` | 2 |
| 每分钟重投全部 queued | `backend/app/modules/scheduler/tasks.py` | 3 |
| 业务 ValueError 分类错误 | `backend/app/modules/scheduler/tasks.py` | 5 |
| IntegrityError 回滚整批 | `backend/app/modules/scheduler/service.py` | 4 |
| 补发 max 使用 UTC | `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx` | 6 |
