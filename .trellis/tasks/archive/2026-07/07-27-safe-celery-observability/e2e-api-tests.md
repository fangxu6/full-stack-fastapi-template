# API E2E Validation Plan

## Scope

本任务没有新增 HTTP API。以下验证确认 HTTP 请求日志与 Celery 任务日志隔离；任务生命周期采用 Celery eager/integration 测试验证。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | HTTP 请求后执行 runtime task | 正常 HTTP request 与 eager `runtime.ping` | 调用 health/read endpoint，再触发 task | HTTP 维持现有响应 | task 日志仅含 task id/name，不含 request id/actor kind | task 日志不含 HTTP path、token 或请求 payload |
| E2E-002 | 失败 task 后执行成功 task | 注入失败 task 和随后成功 task | 依次执行 | 业务失败语义不变 | 后一个 task 无前一个 task context | 失败日志不含 exception text/args/业务 ID |

## Execution

- 使用隔离日志 sink 捕获 JSON 行。
- 任务注册、信号触发和敏感字段验证由后端测试完成；无浏览器步骤。
