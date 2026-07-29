# Implementation Plan

1. 在前三个子任务已合并的基础上，盘点四类 SMTP 生产者、模板和 scheduler alert throttle 路径。
2. 定义 `EmailOutboxKind`、`EmailOutboxStatus`、审计化 `EmailOutbox` 和最小 `services/email_outbox.py`，添加 `email_` 命名约束、partial due index 和 Alembic migration。禁止创建 DTO、管理 API、通用模板协议或额外队列。
3. 实现受控 producer：managed active-user welcome、password recovery、test email、runtime 09:00 test 与 scheduler alerts；认证 HTTP producer 使用 `AuditedWriteSessionDep`，无认证/worker producer 显式绑定 System Actor；删除同步 SMTP 调用和明文 initial-password 模板路径。
4. 实现 minute scanner 与 ID-only delivery task：恢复过期租约、提交后发布 ID、`FOR UPDATE` 领取、SMTP 事务外调用、同 lease 结果落库、15 分钟/8 次 retry、链接 recipient validation。复用库存日报的三段事务形状，但不提取共享基类。
5. 更新测试邮件 API 为 202 queued；保持恢复响应的枚举安全和其他成功响应兼容。运行生成器审阅 OpenAPI 产生的 202 变更。
6. 增加 focused outbox 状态机与 producer API 测试，并回归库存日报专用 delivery 表；运行迁移、eager Celery、SMTP stub 与 API 测试。

## Validation

- `python -m pytest backend/tests/api backend/tests/core backend/tests/modules/scheduler backend/tests/modules/inventory`
- 隔离 PostgreSQL 执行 Alembic upgrade/downgrade/re-upgrade，检查 outbox 约束和 System Actor 外键。
- 用 SMTP stub 覆盖单 recipient 成功、失败、缺配置、lease expiry、8 次终止、success 不重发和 recipient invalid。
- 断言所有 link kind 行的 `subject`/`html_content` 均为 NULL，且 schema/模板/日志中不出现 initial password 或 JWT 持久化。
- 验证 outbox row 不包含 initial password/JWT，日志输出不包含 email、HTML、token、actor UUID 或异常文本。
- 如 OpenAPI 的 test-email 响应改变，运行 `scripts/generate-client.sh` 并将生成产物按 Workflow Phase 3.4 单独审阅提交。

## Review Gate

已复核迁移模型、三种邮件 kind、actor/链接再校验、scheduler 同事务 throttle、账户密码兼容边界和失败状态机；任务现已启动。禁止将库存日报并入通用 outbox。
