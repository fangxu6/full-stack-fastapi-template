# 定时任务 Cron 后续时点预览 API E2E 测试计划

## Environment

- Default target backend: `http://127.0.0.1:8000`
- Health check: `GET /api/v1/utils/health-check/`
- Browser target: `http://localhost:5173`
- Isolation: 使用任务选定的独立 PostgreSQL 测试数据库和测试账户；不得写入开发数据库。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `GET /api/v1/scheduler/cron-preview` | 具备 `scheduler.jobs.read` 的测试用户；服务时钟固定为 `2026-07-26T00:00:00Z`。 | `cron_expression=0 8 * * *` | 200；`base_at` 为固定 UTC 值，`timezone=Asia/Shanghai`，`next_run_ats` 精确为接下来五个上海 08:00 时点且升序。 | 不创建/更新 job、run、审计字段或 Celery 消息。 | 结果首项严格晚于基准；不返回 dispatch lease 等内部字段。 |
| E2E-002 | `GET /api/v1/scheduler/cron-preview` 跨月和日/周 AND | 同上；固定时钟接近月末。 | 分别请求跨月 Cron 与 `0 8 1 * 1`。 | 200；五项与 `next_run_at()` 相同，日/周同时受限时仅返回同时匹配的时点。 | 无持久化或投递。 | 不得用另一 Cron 库或浏览器端结果替代服务端语义。 |
| E2E-003 | 无效 Cron | 已记录 `SchedulerJob`、`SchedulerRun` ID 和 dispatch 调用。 | 缺段/六段/非法 Celery 字段的 `cron_expression`。 | 422；统一 `detail` 与非空 `request_id`。 | job/run ID、审计字段和 dispatch 调用均不变。 | 不返回 500，不新增任务或 Celery 消息。 |
| E2E-004 | 无 read 权限 | 已认证但不含 `scheduler.jobs.read` 的用户。 | 合法 `cron_expression`。 | 403；统一 `detail` 与非空 `request_id`。 | 无持久化或投递。 | 前端不可将隐藏入口当作授权替代。 |
| E2E-005 | 未保存 Cron 的浏览器预览 | 已登录 read 用户，编辑器打开；Playwright 时钟固定且 preview API 可观察。 | 在表单输入未保存的 `0 8 * * *`，等待 300ms 去抖。 | 自动发起一次 preview 请求；界面以上海时间显示基准和五项结果。 | 不触发保存、job/run 变更或 Celery。 | 旧 `next_run_at` 不作为新表单的预览显示。 |
| E2E-006 | 自动预览错误替换 | 同 E2E-005，先获得合法预览。 | 输入无效 Cron，等待去抖；再输入另一合法 Cron。 | 当前错误内联出现，无全局错误提示；新输入开始后旧结果/错误消失，新成功结果替换。 | 不触发保存、job/run 变更或 Celery。 | 输入未完成时不得保留前一 Cron 的时点，也不得阻断保存。 |

## Execution

1. 启动或验证所选隔离环境，并通过 health check。
2. 先运行 E2E-001 至 E2E-004 的 API 用例；随后运行 E2E-005 和 E2E-006 的浏览器用例。
3. 在 `implement.md` 或任务验证记录中写明实际数据库、执行命令、结果及任何具体环境阻塞。

## Validation Record

- Executed against the isolated `aiadmin_test` database. Windows reserved the
  default 8000 port locally, so this validation used `http://127.0.0.1:9000`;
  the browser remained at `http://localhost:5173`.
- Focused API and service cases passed (28 tests), including fixed-clock
  successful responses, cross-month progression, day/week AND behavior,
  invalid Cron 422, read-permission 403, and unchanged job/run rows.
- The scheduler browser suite passed (4 tests). It covers the 300ms automatic
  preview of an unsaved Cron, Shanghai rendering, removal of stale data, and
  inline invalid-Cron feedback.
- A final authenticated HTTP call to the live temporary backend returned the
  `Asia/Shanghai` marker, exactly five values, and values strictly after the
  server-returned base time.
