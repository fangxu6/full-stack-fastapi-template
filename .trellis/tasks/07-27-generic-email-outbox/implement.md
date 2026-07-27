# Implementation Plan

1. 在前三个子任务已合并的基础上，盘点四类 SMTP 生产者、模板和 scheduler alert throttle 路径。
2. 定义 outbox enum/model/schema/service，添加带命名约束的 Alembic migration 和 audit hook 集成。
3. 实现受控 producer：welcome、password recovery、test email、runtime 09:00 test 与 scheduler alerts；删除同步 SMTP 调用和明文 initial-password 模板路径。
4. 实现 minute scanner 与 ID-only delivery task：领取、lease、SMTP 外部调用、结果落库、15 分钟/8 次 retry、recipient validation。
5. 更新测试邮件 API 为 202 queued；保持恢复响应的枚举安全和其他成功响应兼容。
6. 对库存日报做回归，确认其仍使用专用 delivery 表；运行迁移、eager Celery、SMTP stub 与 API 测试。

## Validation

- `python -m pytest backend/tests/api backend/tests/core backend/tests/modules/scheduler backend/tests/modules/inventory`
- 隔离 PostgreSQL 执行 Alembic upgrade/downgrade/re-upgrade，检查 outbox 约束和 System Actor 外键。
- 用 SMTP stub 覆盖单 recipient 成功、失败、缺配置、lease expiry、8 次终止、success 不重发和 recipient invalid。
- 验证 outbox row 不包含 initial password/JWT，日志输出不包含 email、HTML、token、actor UUID 或异常文本。
- 如 OpenAPI 的 test-email 响应改变，运行 `scripts/generate-client.sh` 并将生成产物按 Workflow Phase 3.4 单独审阅提交。

## Review Gate

审核迁移模型、三种邮件 kind、actor/链接再校验、scheduler 同事务 throttle 以及失败状态机后，才可 `task.py start`。禁止将库存日报并入通用 outbox。
