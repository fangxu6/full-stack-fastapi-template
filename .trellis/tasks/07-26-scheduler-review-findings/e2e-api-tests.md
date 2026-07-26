# 定时任务管理审查问题 E2E 验证计划

## Environment

- PostgreSQL 数据库名必须以 `_test` 或 `_pytest` 结尾。
- Redis 使用独立测试实例；Celery Worker/Beat 使用默认队列和 `--concurrency=1`。
- SMTP 使用 mock 或测试 transport，不配置真实收件人。
- 所有时间用固定 UTC clock，显示和 Cron 断言按 `Asia/Shanghai`。

## Cases

| ID | Flow | Setup / Action | Expected |
| --- | --- | --- | --- |
| SRF-E2E-001 | `.env` CSV | 临时 `.env` 设置两个逗号分隔邮箱并创建 `SchedulerSettings` | 两个邮箱成功加载；非法或大小写重复值启动失败。 |
| SRF-E2E-002 | Worker fail-fast | production 缺 SMTP 或收件人，启动 Celery Worker | 进程在 app 导入阶段非零退出，不进入消费循环。 |
| SRF-E2E-003 | Beat fail-fast | 同上，启动 Celery Beat | 进程非零退出；local 配置可启动到应用加载完成。 |
| SRF-E2E-004 | HTTP isolation | production 缺调度告警配置，导入/启动 FastAPI app | HTTP app 正常启动；不提前导入 Celery app。 |
| SRF-E2E-005 | Credential rejection | POST job，配置模型含嵌套 Secret/union，或 JSON 含 `credential`/`authorization`/`access_key` | 422；`scheduler_job` 和 `scheduler_run` 不保存配置。 |
| SRF-E2E-006 | First dispatch | 创建自动、立即运行和补发 run | 每个 run 尽快投递一次，消息参数只有 run ID。 |
| SRF-E2E-007 | Dispatch throttling | Worker 忙碌使 run 保持 queued，连续执行两次分钟扫描 | visibility timeout 前不重复投递；扫描每批不超过 100 条。 |
| SRF-E2E-008 | Dispatch recovery | broker 首次发送失败或模拟发送边界中断 | DB run 保持 queued，后续到期扫描可重投；不创建第二个 active run。 |
| SRF-E2E-009 | Business ValueError | 合法实现类在 `run()` 抛 `ValueError` | run 为 FAILED/EXECUTION_FAILED，发送 FAILURE 类告警。 |
| SRF-E2E-010 | Config failure | 冻结类路径或配置在 Worker 侧失效 | run 为 FAILED/CONFIGURATION_INVALID，发送 CONFIGURATION 类告警。 |
| SRF-E2E-011 | Concurrent run creation | 人工 run 与 scanner 同时为同一 job 创建 active run | 只有一个 active run；另一条按 API 409 或自动 overlap 处理。 |
| SRF-E2E-012 | Batch conflict isolation | 同批两个 due job，其中一个在插入时发生唯一冲突 | 无冲突 job 的 run 和两个 job 的时点推进按预期提交，不发生整批回滚。 |
| SRF-E2E-013 | Shanghai backfill | 固定当前时刻为 `00:30Z`，打开补发弹窗并提交最近上海时间 | max 显示 `08:30`；提交值转换回对应 UTC，浏览器不拦截。 |
| SRF-E2E-014 | Migration | 升级含既有 queued/terminal runs 的数据库，再降级 | queued 的 `next_dispatch_at=created_at`，其他为 NULL；索引和列可逆。 |

## Regression

- 父任务现有 scheduler service/tasks/API、Celery 注册、inventory scheduled task 测试全部通过。
- Worker 执行仍使用默认队列、晚确认、visibility timeout 和单并发配置。
- 固定 Beat 仍只有测试邮件、scheduler scan 和 90 天 cleanup；不恢复 inventory 重复计划。
- 前端 read/manage 权限、任务 CRUD、立即运行、补发和历史列表行为不变。
