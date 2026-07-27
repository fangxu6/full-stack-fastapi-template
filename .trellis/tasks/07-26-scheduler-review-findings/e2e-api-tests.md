# 定时任务管理审查问题 E2E 验证计划

## Environment

- PostgreSQL 数据库名必须以 `_test` 或 `_pytest` 结尾。
- Redis 使用独立测试实例；Celery Worker/Beat 使用默认队列和 `--concurrency=1`。
- SMTP 使用 mock 或测试 transport，不配置真实收件人。
- 所有时间用固定 UTC clock，显示和 Cron 断言按 `Asia/Shanghai`。

## Cases

| ID | Endpoint / flow | Setup data | Request / action | Expected response | Persistence / side effect | Failure assertion |
| --- | --- | --- | --- | --- | --- | --- |
| SRF-E2E-001 | Settings CSV | 临时 `.env` 与进程环境各提供两个 CSV 邮箱 | 创建 `SchedulerSettings` | 两个邮箱被解析；非法或大小写重复值抛校验错误 | 不写数据库 | `NoDecode` 不得被回退为 JSON 预解码。 |
| SRF-E2E-002 | Celery Worker fail-fast | `ENVIRONMENT=production`，缺 SMTP 或收件人 | 启动 `celery -A app.core.celery:celery_app worker` | 进程非零退出 | 不连接 broker、不消费消息 | 异常不能只被 signal 记录后继续启动。 |
| SRF-E2E-003 | Celery Beat fail-fast | 与 SRF-E2E-002 相同；另设 `local` 对照 | 启动 Beat | production 非零退出；local 可完成应用加载 | 不创建 scheduler run | Worker 与 Beat 采用相同的启动边界。 |
| SRF-E2E-004 | HTTP isolation | 与 SRF-E2E-002 相同 | 启动 FastAPI 或请求 `GET /api/v1/utils/health-check/` | HTTP 可用 | 不触发 Celery runtime 校验 | HTTP router 不得因告警配置缺失失败。 |
| SRF-E2E-005 | `POST /api/v1/scheduler/jobs` | manage 用户；测试专用允许类声明嵌套 Secret、union 或敏感键配置 | 提交 `credential`、`authorization`、`access_key` 或 Secret schema 配置 | 422，统一 `detail` 与 `request_id` | `scheduler_job` 与 `scheduler_run` 均无新增快照 | 不扫描、清洗或轮换历史 JSONB；已确认不存在历史凭据。 |
| SRF-E2E-006 | 自动、立即与补发 dispatch | 有效 job 与 mock broker | 扫描 due job；`POST /jobs/{id}/run-now`；`POST /jobs/{id}/backfill` | 手工端点返回 queued run | 每条新 queued run 仅传递 `run_id` 并立即获得一次投递机会 | 终态 run 不得进入投递查询。 |
| SRF-E2E-007 | Dispatch throttling | 100+ queued runs、Worker 忙碌、固定时间 | 连续两次扫描 | 扫描正常完成 | 每批最多 100 条；visibility timeout 前不重复投递 | 默认队列不得按分钟累积同一 run 的重复消息。 |
| SRF-E2E-008 | Dispatch recovery | mock broker 首次失败或发送边界中断 | 执行扫描并推进时间 | run 保持 `QUEUED`，后续到期后可重投 | 不创建第二个 active run | broker 单条失败不能终止同批其他投递。 |
| SRF-E2E-009 | `scheduler.execute_run(run_id)` business failure | 合法任务类的 `run()` 抛 `ValueError` | 执行 worker task | run 为 `FAILED/EXECUTION_FAILED` | 记录 FAILURE 限频字段并发送 FAILURE 告警 | 不得标记为 `CONFIGURATION_INVALID`。 |
| SRF-E2E-010 | `scheduler.execute_run(run_id)` config failure | 冻结类路径或配置失效 | 执行 worker task | run 为 `FAILED/CONFIGURATION_INVALID` | 记录 CONFIGURATION 限频字段 | 不调用任务业务 `run()`。 |
| SRF-E2E-011 | `POST /jobs/{id}/run-now` 与扫描并发 | 同一 job、两个事务屏障 | 同时创建人工和自动 active run | 人工为 409 或自动为 overlap skip | 仅一条 `QUEUED/RUNNING` run | 不依赖先查后插作为唯一并发控制。 |
| SRF-E2E-012 | Scanner batch conflict isolation | 两个 due job；其中一个制造唯一索引冲突 | 扫描批次 | 扫描正常完成 | 无冲突 job 的 run 与两个 job 的 `next_run_at` 均提交 | 冲突只回滚 savepoint，不能回滚整个扫描批次。 |
| SRF-E2E-013 | `/scheduler/jobs` backfill UI | 固定当前时间 `00:30Z`，有 manage 权限会话 | 打开补发弹窗，输入上海最近时间并提交 | 浏览器接受 max `08:30`，请求 payload 转为对应 UTC | 创建 `MANUAL_BACKFILL` run | 不得以 UTC 文本作为 `datetime-local.max`。 |
| SRF-E2E-014 | Migration | 含 queued 与 terminal run 的隔离数据库 | upgrade 新 revision 后 downgrade | upgrade/downgrade 均成功 | queued 行回填 `next_dispatch_at=created_at`，其他为 NULL | 索引与列按依赖顺序移除，不影响既有 run 数据之外的表。 |

## Regression

- 父任务现有 scheduler service/tasks/API、Celery 注册、inventory scheduled task 测试全部通过。
- Worker 执行仍使用默认队列、晚确认、visibility timeout 和单并发配置。
- 固定 Beat 仍只有测试邮件、scheduler scan 和 90 天 cleanup；不恢复 inventory 重复计划。
- 前端 read/manage 权限、任务 CRUD、立即运行、补发和历史列表行为不变。
