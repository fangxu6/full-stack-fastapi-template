# API E2E Validation Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: 独立测试 PostgreSQL、eager Celery 与 SMTP stub；不得向开发 SMTP 发送邮件。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | 创建 active managed user | 管理权限与 SMTP stub | `POST /api/v1/users/` 合法 payload | 现有创建响应 | 同事务创建 ACCOUNT_SET_PASSWORD outbox；HTTP 不调用 SMTP | 禁用用户不创建 invitation；无明文 password 持久化 |
| E2E-002 | 密码恢复 | active user、unknown user、inactive user、System Actor | `POST /api/v1/password-recovery/{email}` | 所有分支保持同一枚举安全成功响应 | 仅 active non-System user 创建 PASSWORD_RECOVERY row | 不存在用户状态泄漏或 token 持久化 |
| E2E-003 | 测试邮件排队 | 管理权限与任意合法 recipient | `POST /api/v1/utils/test-email/` | `202` 与 `Test email queued` | 只创建 RENDERED outbox；scanner/worker 后续处理 | HTTP 不同步 SMTP、不直接 `.delay()` |
| E2E-004 | scheduler alert | 启用 job、configured recipients、失败/overlap 条件 | 触发 scanner/task 流程 | 现有 scheduler 行为 | throttle 与每 recipient rendered outbox 同事务写入 | 无 recipient 时不建 outbox，仍保留限频日志 |

## Execution

- 先确认健康检查与隔离数据库。
- worker 领取和 SMTP 状态转移由 eager/integration 测试验证；E2E 只断言 HTTP 的 durable enqueue 边界。
