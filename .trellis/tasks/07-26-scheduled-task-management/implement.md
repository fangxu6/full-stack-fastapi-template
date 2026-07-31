# 定时任务管理系统实施计划

## Delivery order

1. **Scheduler foundation**
   - 新建 `backend/app/modules/scheduler/`：受限类路径解析器、Celery Cron helper、
     `ScheduledTask` 基类/上下文、调度专用 settings、服务层和 Celery tasks。
   - 使用 Celery `crontab`，不新增 Cron 依赖。单一 helper 负责五段解析、上海时区匹配、
     Cron AND 语义和严格下一时点计算。
   - 在配置持久化及运行快照创建前递归拒绝凭据键和 `SecretStr` 配置，确保 JSONB 永不写入
     密码、token、secret 或连接串。

2. **Database and bootstrap**
   - 新增 `backend/app/models/scheduler.py`，定义 `SchedulerJob`、`SchedulerRun`、状态和触发
     枚举；`SchedulerJob` 复用 `AuditFields`，`SchedulerRun` 仅保留技术时间与可选请求人。
   - 更新 `backend/app/models/__init__.py` 导出模型；新增 `backend/app/schemas/scheduler.py` 的
     严格 create/update/action/public DTO。
   - 生成 `create_scheduler_task_tables` Alembic revision，显式创建 BIGINT identity、UTC 字段、
     `scheduler_` 名称的外键/索引/检查/部分唯一索引和降级路径。
   - 扩展 `init_db`：IAM bootstrap 成功后使用 `FIRST_SUPERUSER` 的已持久真实用户调用
     scheduler bootstrap。用内部 `bootstrap_key` 插入两条库存任务且永不覆盖既有配置。
   - 更新测试 fixture 的导入与清理顺序，先删 runs 再删 jobs。

3. **Scheduling lifecycle**
   - 实现 job CRUD、启停、软删除/恢复、run 创建、领取、完成、失败、取消和清理的服务函数；
     所有变更使用明确 actor，定义服务返回 404/409/422 的现有异常类型。
   - 扫描任务锁定到期 job：只有同一上海分钟内创建 `QUEUED` run；过期时点直接推进，
     活动冲突创建 `SKIPPED` run 并触发限频告警。
   - 运行器仅接收 `run_id`，领取时设置 lease；Celery 重投时只允许过期 lease 重领。执行类
     后写终态、安全类别和泛化摘要，绝不持久化 traceback 或返回值。
   - 实现每日 03:30 cleanup，仅删除 90 天前的终态 runs。

4. **Runtime and inventory integration**
   - 扩展 `backend/app/core/celery.py` 的 include，保留每日测试邮件，加入每分钟扫描和每日
     cleanup；删除库存创建/retry 固定 Beat 条目。
   - 保持 `celery.py` 对 SMTP 和告警收件人配置无启动前依赖；调度告警通过通用
     `email_outbox` 持久化，空收件人记录 `scheduler.alert.unsent`，SMTP 不可用由 outbox 重试。
   - 增加 `backend/app/modules/inventory/scheduled_tasks.py` 两个适配类；保留
     `inventory.daily_report.deliver` 注册，移除不再需要的 create/retry Celery 注册。
   - 创建日报适配类用实际运行开始时间调用既有窗口函数；08:15 后将 scheduler run 记为
     `SKIPPED`，不创建日报。

5. **HTTP and RBAC**
   - 在 `backend/app/modules/iam/constants.py` 增加 scheduler read/manage 和依赖；更新前端
     `PermissionCode` 联合类型。
   - 新建 scheduler router，注册到 `backend/app/api/main.py`；实现设计中的任务、运行历史和
     Schema 端点，所有列表用 `data + count`、`skip/limit`。
   - 在配置成功更新、运行成功或异常发生时按设计维护三类限频字段；SMTP 失败不覆盖原运行
     状态。
   - 重新生成 OpenAPI 前端 client，禁止手写生成服务类型。

6. **Frontend**
   - 新增 `/scheduler/jobs` TanStack route、feature 页面和局部组件；用 existing Ant Design
     Table、Modal/Drawer、React Query 与服务端分页模式。
   - 添加按 read 权限过滤的侧栏入口及 route guard。manage 权限控制所有写操作。
   - 实现 JSON 文本配置、Schema 查看、类/配置服务端错误、启停、确认删除、立即执行、
     上海时区补发输入和分页运行历史。不要添加动态表单、Cron 预览、通用组件或新 UI 库。

7. **Configuration and documentation**
   - 在 `.env` 和 `.env.production.example` 增加空的
     `SCHEDULED_TASK_ALERT_RECIPIENTS=` 示例；说明逗号分隔格式，不写真实邮箱。
   - 更新 `backend/README.md` 的部署顺序，强调升级后运行 `python app/initial_data.py`，再启动
     PM2 Worker/Beat；无需新增 PM2 app。

## Test plan

### Backend unit and service tests

- 新增 `backend/tests/modules/scheduler/test_config.py`：收件人 CSV、大小写去重、local 与
  staging/production 启动校验。
- 新增 `test_cron.py`：五段格式、Celery AND 语义、上海时区、同一分钟可执行、跨分钟错过和
  下一时点计算。
- 新增 `test_service.py`：严格类路径、基类、Pydantic config、递归凭据拒绝、默认停用、
  启停、软删除/恢复、audit fields、90 天补发和冻结快照。
- 新增 `test_tasks.py`：扫描创建、错过推进、活动冲突 skip、Worker 领取、取消 no-op、
  lease 重领、成功/失败安全摘要、无通用业务 retry、90 天清理和告警限频/清除规则。
- 扩展 `backend/tests/core/test_celery.py`：scheduler tasks 已注册，库存固定 Beat 条目不存在，
  测试邮件保留。
- 扩展 `backend/tests/modules/inventory/test_daily_report.py`：通过适配类验证实际 08:15 后
  运行跳过，且原投递任务仍可领取。

### API and migration tests

- 新增 `backend/tests/api/routes/test_scheduler.py`：read/manage 403、定义 CRUD、Schema、
  分页、软删除、恢复、run now、补发、冲突、422 验证和冻结快照。
- 验证 `init_db` 在 IAM 完成后创建且只创建两条 `bootstrap_key` 任务，不覆盖编辑过的 Cron/
  配置/启用状态。
- 使用隔离 `_test` 或 `_pytest` 数据库运行升级到 head；断言模型/迁移的 identity、命名、
  外键、部分唯一 active-run 索引和 cleanup fixture。

### Frontend tests

- 生成 client 后执行 TypeScript build。
- 覆盖权限入口、route guard、分页 query key、manage-only 操作、JSON 错误和补发输入到
  API 请求的时区转换。现有 Playwright 基础设施可补充关键管理流，但不在浏览器中伪造
  Celery 运行。

## Validation commands

```powershell
Set-Location backend
uv run alembic upgrade head
uv run python app/initial_data.py
uv run pytest tests/modules/scheduler tests/api/routes/test_scheduler.py tests/core/test_celery.py tests/modules/inventory/test_daily_report.py
uv run ruff check app tests
uv run ty check app

Set-Location ../frontend
bun run generate-client
bun run build
```

运行全量测试前，`POSTGRES_DB` 必须是以 `_test` 或 `_pytest` 结尾的隔离数据库。验证生产
启动配置时，使用独立环境运行 Worker 和 Beat；不要对开发库执行迁移或清理测试。

## Risk and rollback

| Risk | Mitigation | Rollback point |
| --- | --- | --- |
| 类路径在部署后失效 | 同步验证、运行记录失败、限频邮件、保持启用便于代码修复后恢复 | 修复代码或有效保存配置；不自动停用。 |
| Worker 崩溃导致重复 | run lease + late ack + 业务幂等；只重领同一 run | 停止 Worker，检查 run 历史和业务幂等结果。 |
| 扫描/定义迁移重复日报 | 删除等价 static Beat，bootstrap key 只插入一次，日报原有 unit/date 唯一约束仍在 | 先停止 Beat/Worker，再回退；降级会删除 scheduler 数据。 |
| 告警收件人为空或 SMTP 不可用 | Worker/Beat 保持可用；空收件人记录安全日志，已有 outbox 行按其投递策略重试 | 补齐配置后等待下一次告警或 outbox 重试。 |
| 软删除定义误操作 | 仅软删，运行历史保留 90 天，可恢复为停用 | 恢复后检查配置并显式启用。 |

## Files with highest change risk

- `backend/app/core/celery.py`: 修改静态 Beat 和 task include，必须防止重复库存投递。
- `backend/app/core/db.py`: 初始化顺序必须在 IAM bootstrap 后且不改变首个管理员保证。
- `backend/app/modules/inventory/tasks.py` / `daily_report.py`: 只适配调度入口，不能改变库存
  快照和 SMTP delivery 语义。
- `backend/tests/conftest.py`: 新模型清理顺序必须尊重 run -> job 外键。
- `frontend/src/client/*`: 仅由生成器更新；页面使用生成后的方法和类型。
