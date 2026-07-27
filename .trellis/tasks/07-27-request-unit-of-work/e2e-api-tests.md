# API E2E Validation Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: 使用独立测试 PostgreSQL 数据库；不得写入开发数据库。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | 用户或 items 成功创建 | 已认证可写用户 | 合法 `POST` payload | 现有成功状态与响应模型 | 业务行在 endpoint 成功后提交一次 | 无额外 commit，响应后可由新 Session 查询到行 |
| E2E-002 | 库存或 IAM 写校验失败 | 已认证用户与必要关联行 | 触发业务/完整性错误的写请求 | 现有统一 4xx/5xx 错误形状 | 本请求已创建或更新的所有行均回滚 | 不产生半写入业务行、审计行或 future outbox 行 |
| E2E-003 | 手工 scheduler run | 已认证管理员和启用 job | 创建一次运行 | 现有成功响应 | run 先持久化为 `QUEUED`；无提交前 broker 发布 | scanner 在独立后续事务处理投递 |

## Execution

- 先验证隔离环境健康检查。
- 对每个已迁移模块重复 E2E-001/E2E-002，并记录未覆盖模块。
- 在实现完成后运行对应 API tests；任何失败先回到该模块的事务边界而非在 endpoint 临时补 commit。
