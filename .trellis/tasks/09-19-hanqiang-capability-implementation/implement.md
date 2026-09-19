# 实施计划：事件回调内核

> 2026-09-19 复核版；本轮只更新规划。功能实现和下列运行时验证均未执行。

## 前置门槛

- [x] 保留已确认的内核范围；Webhook、业务适配器和管理功能见 [deferred-iterations.md](deferred-iterations.md)。
- [x] 需求与当前源码/规范复核；记录见 [research/requirements-review.md](research/requirements-review.md)。
- [x] [prd.md](prd.md)、[design.md](design.md)、[e2e-api-tests.md](e2e-api-tests.md) 覆盖语义、状态和跨层验证。
- [ ] 展示本版最终摘要后，收到用户新的明确实施批准。
- [ ] 恢复 Trellis 开发者/会话上下文：本轮 get_context 报 Developer 未初始化；现有 task.json 的 creator/assignee 为 fx，不能据此误判为没有任务或新建重复任务。
- [ ] 确认 task.py validate 通过，implement.jsonl/check.jsonl 为真实 spec/research 路径，然后才可 task.py start。

上下文校验提示 database-guidelines.md 和 async-task-guidelines.md 超过自动注入的单文件上限。实施/检查者必须直接读取相关完整章节（数据库 audit fields、Actor、AuditEvent、中文注释及异步 Scheduler/EmailOutbox），不能把自动注入的截断前缀当作完整规范。

## 顺序清单

1. [ ] 读取当前 backend specs、研究记录和本版契约；确认实际 Alembic head、测试工具链、数据库与 Broker 隔离。
2. [ ] 定义信封、稳定领域错误、处理器注册与版本规则；先用边界数据验证规范化、65,536 字节/32 层限制和快照隔离。
3. [ ] 定义 EventPublication、EventDeliveryState、错误分类与投递模型，建立 migration、唯一/CHECK 约束、partial indexes 和中文注释；更新模型发现及外键安全的测试清理顺序。
4. [ ] 实现事务内 publish；验证事件/投递/审计原子性、并发同 ID、冲突隔离、不同请求上下文、零匹配和历史不补投。
5. [ ] 实现领域内状态服务：派发预占/失败释放、claim、complete/fail/recover。服务无 commit/rollback；检查双租约、token、attempt、终态及 Actor。
6. [ ] 接入扫描/单投递 Celery 任务和分钟级 Beat；独立短事务协调，Broker/handler 无长事务；处理受控异常、提交不确定与敏感异常链。
7. [ ] 仅在日志规范允许范围内增加固定事件名；建立提交后日志、事务内 AuditEvent、旧结果无审计和日志脱敏验证。
8. [ ] 先运行有意义的单元/数据库并发/eager 测试，再执行真实 Redis/Worker 的 E2E 流程及进程故障注入。
9. [ ] 完整后端质量检查与受影响回归；复核 OpenAPI/前端无契约变化，迁移与保留数据的应用回滚演练完成。
10. [ ] 对照 AC-01–AC-11 全范围审查，更新适用 spec 并完成 Trellis check；最后再进入仓库提交和 finish-work 流程。

## 预期影响文件

- `backend/app/models/event.py`、`backend/app/models/__init__.py`
- `backend/app/modules/events/{__init__,contracts,registry,service,tasks}.py`
- `backend/app/core/celery.py`（include/Beat）、`backend/app/core/observability.py`（固定事件名，保留封闭字段）
- `backend/app/alembic/versions/<new_revision>_create_event_callback_kernel_tables.py`
- `backend/tests/conftest.py`（模型/清理顺序）
- `backend/tests/modules/events/`（包含 contracts、service、concurrency、tasks、runtime 集成及迁移检查）
- 既有 `backend/tests/core/test_celery.py`、日志测试的受影响断言

不以扩展通用配置、日志字段、队列或重构其它领域为隐含前置工作。只有真实代码复杂度需要时再拆分 events 内部文件。

## 验证命令与隔离

仓库根目录：

```bash
python ./.trellis/scripts/task.py validate 09-19-hanqiang-capability-implementation
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

真实运行时集成由实施时新增的 `tests/modules/events/test_runtime.py` 执行：

```bash
uv run pytest tests/modules/events/test_runtime.py
```

运行器须自行验证并记录隔离目标、启动独立 Worker、收集结果和清理本次创建的进程/数据；未完成此入口前不得把命令列为已通过。等待使用可轮询的持久化条件和有界超时，避免固定长睡眠。

## 风险与回滚点

- event_id 唯一竞态必须只处理局部冲突；发布方事务中其它业务数据不能被 service.rollback 意外清除。
- AuditFields flush 需要有效 Actor；缺失时失败，不随机填充。首次人工发起与自动重试归属分别验证。
- lease token 防止旧结果覆写，不会取消已发生的副作用；未来消费者负责幂等，当前测试必须展示这一限制。
- 原始 handler/数据库异常可能经 Celery traceback 暴露快照，必须验证正常、受控失败、提交失败和下一任务上下文。
- 应用回滚保留事件表与数据；删表 downgrade 只在上述迁移专用空库演练。
- 无生产消费者不能省略内核失败恢复测试；也不能把未来 retention/超时/业务幂等未确定描述成生产能力完成。

## 完成与证据

- [ ] 按 E2E 表记录每项命令、观察到的响应/状态、副作用、失败分类和 AC 映射。
- [ ] AC-01–AC-11 均有证据；未运行不记为通过。
- [ ] 缺 PostgreSQL/Redis/Worker 时先尝试计划的隔离环境，再记录具体可复现阻塞；不能仅凭“本机可能缺服务”跳过。
- [ ] trellis-check 全范围通过；需要 spec 更新时完成对应维护。
- [ ] 本任务变更提交/归档按仓库流程进行，不能因为文档已校验而跳过运行时质量门槛。
