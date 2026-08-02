# API E2E 验证计划

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Browser target: 不适用，本任务不改变浏览器流程。
- Isolation: 使用已启动的本地 backend；本用例只读取健康端点，不创建测试数据、不写入数据库，且
  启动环境不设置 `SENTRY_DSN`。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | 无 Sentry 配置的应用健康检查 | 启动 backend 时不提供 `SENTRY_DSN`；其他必填设置沿用隔离本地环境 | `GET /api/v1/utils/health-check/` | `200`，JSON `true`，带 `X-Request-ID` | 无数据库写入、无外部 telemetry 初始化或导出 | 任何启动失败、5xx、连接外部 Sentry 的尝试或持久化写入均失败 |

## Execution

- 先确认本地 backend 健康，再在移除变量后的进程执行 E2E-001。
- 记录 HTTP 状态、响应体和 request ID；若环境不满足，先尝试隔离启动，仍受阻时在任务验证记录具体原因。
- 此用例不替代 focused Python 回归测试、`uv lock --check` 或配置/文档范围检查。
