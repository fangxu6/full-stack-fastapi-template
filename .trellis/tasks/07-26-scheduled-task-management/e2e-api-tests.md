# 定时任务管理系统 API E2E 测试计划

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `GET /api/v1/utils/health-check/`
- Browser target: `http://localhost:5173`
- Isolation: `POSTGRES_DB` 必须使用 `_test` 或 `_pytest` 后缀的数据库；测试前运行 Alembic
  upgrade 和 `python app/initial_data.py`。不得向开发数据库创建任务定义或运行记录。
- Celery: 单独测试环境的 Redis、Worker 和 Beat；SMTP 用 mock 或测试 SMTP，绝不使用真实
  运维收件人。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `GET /scheduler/jobs` | 有 read 权限用户与多条定义 | `skip=0&limit=20` | 200，`{data,count}` | 默认排除软删除行 | 无 read 权限为 403；分页越界为 422。 |
| E2E-002 | `POST /scheduler/jobs` | manage 用户、测试实现类 | 名称、受限类路径、`0 8 * * *`、`{}` | 200，默认 `enabled=false` | 创建完整审计字段和 UTC `next_run_at` | 非法模块、非基类、6 段 Cron、未知 JSON 字段、凭据键和客户端 audit/id 均为 422。 |
| E2E-003 | `GET /scheduler/task-schema` | 已部署测试实现类 | 合法 `class_path` | 200，Pydantic JSON Schema | 无写入 | 受限范围外或无法加载为 422；无 read 权限为 403。 |
| E2E-004 | 更新与快照 | 已有 definition 和 queued run | `PUT /jobs/{id}` 更新 Cron/config | 200，定义更新且 `next_run_at` 重算 | 原 queued run 的 class/config 保持原值 | 非法更新不改变定义或 run。 |
| E2E-005 | 启用与扫描 | 停用定义，`next_run_at` 位于当前上海分钟 | `POST /enable` 后执行扫描 | 200；扫描创建 queued run | 运行冻结快照，定义推进下一时点 | 超过同一分钟只推进，不创建补跑 run。 |
| E2E-006 | 活动冲突 | 同一 job 已有 queued/running run | 扫描同一计划时点 | 扫描完成 | 增加 `SKIPPED/OVERLAP` run、推进时点、按限频告警 | 不存在第二条 active run；手工操作返回 409。 |
| E2E-007 | Worker lifecycle | queued run，测试实现成功/失败 | 投递 `scheduler.execute_run(run_id)` | Celery 成功完成 | `SUCCEEDED` 或 `FAILED`、实际时间、lease 清理、安全摘要；失败邮件 | 无完整 traceback/业务返回值；失败不自动创建 retry run。 |
| E2E-008 | 停用、删除、恢复 | queued 与 running run | disable、delete、restore | disable 200；active delete 409；restore 200 | queued 变 `CANCELLED`，running 不变；恢复后停用 | cancelled run 被 Worker 领取时 no-op；软删 job 默认列表/扫描均不可见。 |
| E2E-009 | 手工立即运行 | 停用但有效定义 | `POST /run-now` | 200，queued run | `trigger=MANUAL_NOW`、`requested_by` 为请求用户、上海当前参考时点 | 不需要 enabled；活动 run 时 409。 |
| E2E-010 | 单时点补发 | 有 Cron 定义 | `POST /backfill`，过去且命中 Cron 的 +08:00 时间 | 200，queued run | `trigger=MANUAL_BACKFILL`、冻结所选时点和请求人 | 未来、无时区、未命中或超过 90 天为 422。 |
| E2E-011 | 运行历史 | 多种 run 终态 | `GET /jobs/{id}/runs` 分页 | 200，`{data,count}` | 仅安全字段和快照 | 他人 job/软删 job 404；无 read 403。 |
| E2E-012 | 告警限频 | 收件人、SMTP mock、失败/重叠/配置失效定义 | 连续触发同类别，再触发成功或有效更新 | 原操作正常完成 | 每任务每类别每小时创建一组耐久 outbox 行；成功清运行/重叠限频，有效更新清配置限频 | SMTP 失败不改写 run 状态；手工 409 不发邮件。 |
| E2E-013 | Runtime config | staging/production 样例环境，缺收件人或 SMTP | 启动 Worker/Beat | 进程可启动 | HTTP API 同样可用；空收件人只记录 `scheduler.alert.unsent` 并推进限频 | 不得因告警投递配置阻塞 Celery 导入或启动。 |
| E2E-014 | Inventory bootstrap | 干净升级数据库、已初始化管理员 | 运行 `initial_data.py` 两次 | 均成功 | 只创建两条 bootstrap-key 任务且启用，不覆盖人工编辑 | 固定 inventory create/retry Beat 条目不存在。 |
| E2E-015 | Inventory timing | 每日创建 job 在 08:00 queued，实际执行 08:16 上海 | 执行 run | run 为 `SKIPPED` | 不创建库存日报；投递任务注册保持 | 08:01 运行仍复用原逻辑创建日报。 |
| E2E-016 | Retention | 90 天前终态与活动 run | 运行 cleanup task | 清理完成 | 仅删除过期终态 run，definition 保留 | 活动、90 天内或无 `finished_at` 的 run 不删除。 |

## Browser smoke flow

1. 使用有 `scheduler.jobs.read` 权限的用户登录，确认侧栏出现“定时任务”且列表可分页。
2. 使用无 manage 权限用户，确认新增、编辑、开关、执行和删除操作不显示，直接 API 写操作为
   403。
3. 使用 manage 用户新建合法测试任务，查看 Schema，输入无效 JSON 后看到服务端错误；修正后
   保存为停用，再启用并查看下一时点。
4. 执行“立即运行”和一个 90 天内匹配的补发，确认运行历史显示正确触发方式与安全摘要。
5. 停用含 queued run 的任务，确认 run 显示取消；恢复软删定义后确认其仍停用，需显式启用。

## Execution

```powershell
Set-Location backend
uv run alembic upgrade head
uv run python app/initial_data.py
uv run pytest tests/modules/scheduler tests/api/routes/test_scheduler.py

Set-Location ../frontend
bun run generate-client
bun run build
```

执行需要 Worker/Beat 的用例时使用隔离 Redis 和测试 SMTP。记录任何端口、SMTP 或数据库
环境阻塞到 `implement.md` 的验证记录；SMTP 缺失的耐久投递行为由通用 outbox 契约验证。
