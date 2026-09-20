# 实施记录：事件回调内核

> 2026-09-19；已按批准范围完成实现与验证记录。Webhook、业务适配器和管理功能仍延期。

## 前置门槛

- [x] 保留已确认的内核范围；Webhook、业务适配器和管理功能见 [deferred-iterations.md](deferred-iterations.md)。
- [x] 需求与当前源码/规范复核；记录见 [research/requirements-review.md](research/requirements-review.md)。
- [x] [prd.md](prd.md)、[design.md](design.md)、[e2e-api-tests.md](e2e-api-tests.md) 覆盖语义、状态和跨层验证。
- [x] 展示本版最终摘要后，收到用户新的明确实施批准。
- [x] Trellis 开发者/会话上下文已恢复；当前 `get_context.py` 识别开发者 `fx` 和本任务，不新建重复任务。
- [x] 确认 task.py validate 通过，implement.jsonl/check.jsonl 为真实 spec/research 路径，然后执行 task.py start。

上下文校验提示 database-guidelines.md 和 async-task-guidelines.md 超过自动注入的单文件上限。实施/检查者必须直接读取相关完整章节（数据库 audit fields、Actor、AuditEvent、中文注释及异步 Scheduler/EmailOutbox），不能把自动注入的截断前缀当作完整规范。

## 顺序清单

1. [x] 读取当前 backend specs、研究记录和本版契约；确认实际 Alembic head、测试工具链、数据库与 Broker 隔离。
2. [x] 定义信封、稳定领域错误、处理器注册与版本规则；验证规范化、65,536 字节/32 层限制和快照隔离。
3. [x] 定义 EventPublication、EventDeliveryState、错误分类与投递模型，建立 migration、唯一/CHECK 约束、partial indexes 和中文注释；更新模型发现及外键安全的测试清理顺序。
4. [x] 实现事务内 publish；验证发布幂等、冲突隔离、不同请求上下文、处理器快照和无匹配行为。
5. [x] 实现派发预占/失败释放、claim、complete/fail/recover；验证双租约、token、attempt、终态及 Actor。
6. [x] 接入扫描/单投递 Celery 任务和分钟级 Beat；短事务协调、固定错误边界和异常链脱敏已实现。
7. [x] 增加固定日志事件名；审计摘要使用模块 allowlist，旧结果不写审计。
8. [x] 完成单元/数据库/真实 Redis-Worker 基础 E2E 验证；真实 Worker 流程使用测试入口注册处理器并在测试结束清理。进程故障注入等未列入 Execution Record 的场景保留后续。
9. [x] 完成后端 lint/type/format 与受影响 Celery/Outbox/Scheduler 回归；完成迁移往返和应用回滚保留规则复核；无 OpenAPI/前端契约变化。
10. [x] 对照 AC-01–AC-11 完成全范围审查，更新适用 spec 并完成 Trellis check；最后再进入仓库提交和 finish-work 流程。

## 预期影响文件

- `backend/app/models/event.py`、`backend/app/models/__init__.py`
- `backend/app/modules/events/{__init__,contracts,registry,service,tasks}.py`
- `backend/app/core/celery.py`（include/Beat）、`backend/app/core/observability.py`（固定事件名，保留封闭字段）
- `backend/app/alembic/versions/<new_revision>_create_event_callback_kernel_tables.py`
- `backend/tests/conftest.py`（模型/清理顺序）
- `backend/tests/modules/events/`（包含 contracts、registry、service、runtime、tasks 及迁移元数据检查）
- 既有 `backend/tests/core/test_celery.py`、日志测试的受影响断言

不以扩展通用配置、日志字段、队列或重构其它领域为隐含前置工作。只有真实代码复杂度需要时再拆分 events 内部文件。

## 验证命令与隔离

仓库根目录：

```bash
python3 ./.trellis/scripts/task.py validate 09-19-hanqiang-capability-implementation
```

运行时计划必须先明确以下环境，且测试前验证实际连接目标：

- PostgreSQL 专用库 `event_kernel_test` 或 `event_kernel_pytest`；迁移往返使用另一专用空库 `event_kernel_migration_test`，不能对已有测试套件正在使用的库做 downgrade。
- 独立 Redis 进程/实例与任务专用端口，沿用现有 Broker DB0/result DB1；禁止连接开发环境 Worker 或共享默认队列。
- 独立后端 `http://127.0.0.1:8000`、Worker、必要的 Beat。端口占用时先核对环境身份，不向已有未知服务写测试数据。
- 所有进程加载相同数据库、Redis、签名配置；测试 handler 通过测试入口在发布进程和 Worker 明确注册，关闭 eager。不得让 monkeypatch 只存在于父进程却声称验证了真实 Worker。
- 集成 Worker 仅加载本任务需要的任务/测试入口；真实 Beat 场景只启用事件扫描调度，避免顺带触发现有定时邮件。
- Windows 不假定某种 Worker pool 能强杀运行中的 handler；使用测试专用进程终止/恢复做故障注入。后台进程隐藏窗口；不停止用户现有开发服务。

从 backend 目录运行；先设置经过验证的上述隔离环境：

```bash
uv run pytest tests/modules/events tests/core/test_celery.py tests/services/test_email_outbox.py tests/modules/scheduler
bash scripts/lint.sh
uv run ruff check tests/modules/events tests/core/test_celery.py tests/conftest.py
uv run ruff format tests/modules/events tests/core/test_celery.py tests/conftest.py --check
```

`scripts/lint.sh` 包含全 app 的 mypy、ty、Ruff check 和 format check，不能只跑新模块替代。实施后按实际测试位置追加审计/日志回归。Windows 从根目录使用 `bash -lc 'cd backend && ./scripts/lint.sh'`。

迁移专用库：

```bash
uv run alembic upgrade head
uv run alembic downgrade <new_revision的实际父revision>
uv run alembic upgrade head
```

真实运行时集成由 `tests/modules/events/test_runtime.py` 执行：

```bash
uv run pytest tests/modules/events/test_runtime.py
```

运行器须自行验证并记录隔离目标、启动独立 Worker、收集结果和清理本次创建的进程/数据；未完成此入口前不得把命令列为已通过。等待使用可轮询的持久化条件和有界超时，避免固定长睡眠。

## 本轮实际验证证据

- `python3 ./.trellis/scripts/task.py start 09-19-hanqiang-capability-implementation`：任务状态已从 `planning` 切换为 `in_progress`。
- `python3 ./.trellis/scripts/task.py validate 09-19-hanqiang-capability-implementation`：`implement.jsonl` 9 条、`check.jsonl` 11 条真实上下文记录通过；仅有大文件注入截断警告。
- `bash scripts/lint.sh`：`mypy` 112 个 app 源文件、`ty`、Ruff check、Ruff format 全部通过。
- `POSTGRES_DB=event_kernel_pytest uv run pytest tests/modules/events -q`：17 项通过；覆盖契约、注册、迁移元数据、幂等、Actor、派发租约、执行租约、恢复、8 次失败终态和处理器事件类型漂移拒绝。
- `POSTGRES_DB=event_kernel_pytest uv run pytest tests/modules/events tests/core/test_celery.py tests/services/test_email_outbox.py tests/modules/scheduler -q`：96 项通过；使用专用 PostgreSQL 与非默认本地测试密钥/SMTP 配置。
- `POSTGRES_DB=event_kernel_migration_test uv run alembic upgrade head`、`downgrade f6a1b2c3d4e5`、`upgrade head`：独立迁移库往返通过。
- `POSTGRES_DB=event_kernel_pytest REDIS_PORT=6381 uv run pytest tests/modules/events/test_runtime.py -q -s`：真实 Redis 6381、独立 Celery `solo` Worker、跨进程测试处理器通过；最终 delivery 为 `SUCCEEDED`，处理器幂等审计副作用为 1 条；Worker/Redis 已终止清理。
- 本期未新增 HTTP 路由、OpenAPI schema、前端文件或生产处理器；因此未执行前端 client 生成。

早期直接运行测试时使用了缺少项目必填配置或生产环境默认密码的环境，得到配置/连接失败；随后按仓库规范切换到 `event_kernel_pytest`、可用 `postgres` 角色、非默认测试密钥和独立 Redis 后重跑，以上结果为最终结果。生产测试配置不得使用这些本地值。

## 风险与回滚点

- event_id 唯一竞态必须只处理局部冲突；发布方事务中其它业务数据不能被 service.rollback 意外清除。
- AuditFields flush 需要有效 Actor；缺失时失败，不随机填充。首次人工发起与自动重试归属分别验证。
- lease token 防止旧结果覆写，不会取消已发生的副作用；未来消费者负责幂等，当前测试必须展示这一限制。
- 原始 handler/数据库异常可能经 Celery traceback 暴露快照，必须验证正常、受控失败、提交失败和下一任务上下文。
- 应用回滚保留事件表与数据；删表 downgrade 只在上述迁移专用空库演练。
- 无生产消费者不能省略内核失败恢复测试；也不能把未来 retention/超时/业务幂等未确定描述成生产能力完成。

## 完成与证据

- [x] 按 E2E 表记录已执行的命令、隔离目标、状态和副作用证据；未执行的 HTTP 健康检查因本期无 HTTP 入口保持不适用。
- [x] AC-01–AC-11 已进入 Trellis check 做最终逐项审查；未单独执行的故障注入场景仍保留在 E2E 计划中，未记为运行时通过。
- [x] 已尝试并建立计划中的隔离 PostgreSQL、Redis、Worker 环境；测试结束清理本次创建的 Redis/Worker，测试数据库保留为本地隔离验证库。
- [x] trellis-check 全范围通过；已新增 `.trellis/spec/backend/event-callback-guidelines.md` 并更新后端规范索引。
- [ ] 本任务变更提交/归档按仓库流程进行，不能因为文档已校验而跳过运行时质量门槛。
