# 实施计划：事件回调内核

## 前置门槛

- [x] 用户确认本期只实现事件回调内核，Webhook 和具体业务适配器延期。
- [x] 已核对当前模板的 SQLModel、Alembic、AuditEvent、Celery、EmailOutbox 和系统 Actor 模式。
- [x] 已明确无新增 HTTP 路由、前端页面和生成客户端，因此不创建 E2E API 计划。
- [ ] 用户批准本计划摘要后，运行 `task.py start` 进入实施阶段。

## 顺序清单

1. [ ] 创建 `models/event.py`，定义 `EventPublication`、`EventDelivery`、状态 enum、约束、索引和中文数据库注释。
2. [ ] 创建事件模块契约和代码注册表：不可变 `EventEnvelope`、处理器协议、稳定 handler key；禁止动态 import 和任意 callable 配置。
3. [ ] 创建事件服务：事务内 publish、同 event ID 幂等/冲突处理、handler 匹配、claim/complete/fail/recover 状态迁移和审计。
4. [ ] 创建事件 Celery 任务：due scan、过期 lease 恢复、只传 delivery ID 的 process task；接入现有 Celery include 和 Beat schedule。
5. [ ] 创建 Alembic migration；导入模型并验证 upgrade/downgrade、状态 enum、外键、partial index 和中文注释。
6. [ ] 添加模块单元/数据库/Celery eager 测试，使用测试假处理器覆盖成功、重试、终态、幂等、冲突、租约和脱敏。
7. [ ] 运行质量检查，复核没有 HTTP、Webhook、前端、Secret 或业务适配器意外进入 diff。

## 预期代码文件

- `backend/app/models/event.py`
- `backend/app/models/__init__.py`
- `backend/app/modules/events/__init__.py`
- `backend/app/modules/events/contracts.py`
- `backend/app/modules/events/registry.py`
- `backend/app/modules/events/service.py`
- `backend/app/modules/events/tasks.py`
- `backend/app/core/celery.py`
- `backend/app/core/observability.py`
- `backend/app/alembic/versions/<new_revision>_create_event_callback_kernel_tables.py`
- `backend/tests/modules/events/test_contracts.py`
- `backend/tests/modules/events/test_service.py`
- `backend/tests/modules/events/test_tasks.py`

## 验证命令

从仓库根目录执行：

```bash
python3 ./.trellis/scripts/task.py validate 09-19-hanqiang-capability-implementation
```

在 `backend/` 使用仓库管理的环境和隔离的 `POSTGRES_DB`（名称以 `_test` 或 `_pytest` 结尾）：

```bash
uv run pytest tests/modules/events tests/core/test_celery.py
uv run ruff check app/models/event.py app/modules/events app/core/celery.py app/core/observability.py tests/modules/events
uv run mypy app/modules/events app/models/event.py
uv run alembic upgrade head
uv run alembic downgrade <previous_revision>
uv run alembic upgrade head
```

如果运行环境没有 PostgreSQL/Redis，记录具体缺失服务和已完成的纯单元检查，不把测试未运行写成通过。

## 风险与回滚点

- `AuditFields` 要求 flush 前绑定 Actor：服务测试必须显式绑定测试用户，Worker 路径必须绑定系统 Actor；否则应失败而不是生成随机 Actor。
- 模型导入顺序影响 Alembic metadata 和测试清理顺序；新增模型必须加入 `models/__init__.py` 和 `tests/conftest.py` 的清理列表。
- handler 发生外部副作用后 Worker 崩溃会导致 at-least-once 重复调用；本期只验证假处理器，未来 Adapter 必须在自己的任务中承担幂等。
- 事件 payload 过大或包含敏感字段会形成数据库和审计风险；内核限制 JSON object/大小且从不写日志，业务适配器仍需最小快照。
- 如 migration 或状态机验证失败，回滚新增事件模块、Celery include/schedule 和 migration；不触碰现有 EmailOutbox/Scheduler 表。

## 完成门槛

- [ ] `trellis-check` 通过，或记录具体可复现阻塞。
- [ ] 事件内核测试通过，迁移在隔离数据库完成 upgrade/downgrade/upgrade。
- [ ] 代码 diff 不包含 Webhook、HTTP、动态配置、前端或具体业务事件。
- [ ] 必要时更新 `.trellis/spec/`，并运行 spec wiki 维护检查。
- [ ] 通过最终审阅后提交本任务变更，再执行 finish-work。
