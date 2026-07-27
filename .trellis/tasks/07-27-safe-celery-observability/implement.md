# Implementation Plan

1. 列出 Celery 已注册任务和 observability 当前事件/字段白名单。
2. 为任务生命周期增加最小 context bind/clear helper，校验 task id/name 的值域。
3. 在 Celery app 注册 prerun 与终态 signals，终态使用 `try/finally` 清理 context。
4. 扩展封闭的 `EventName`/`log_event()` 签名，保持 HTTP 调用兼容；禁止开放 `**kwargs`。
5. 添加串行成功/失败任务测试、敏感参数回归测试和 HTTP/task context 隔离测试。
6. 运行 Celery eager 任务及现有 observability/scheduler/inventory 测试，确认无 ACK、队列或启动校验回归。

## Validation

- `python -m pytest backend/tests/core/test_observability.py backend/tests/core/test_celery.py backend/tests/modules/scheduler`
- 断言 JSON 事件仅包含 schema fields、environment、timestamp、task id/name 与安全事件名。
- 执行两个连续 eager task，其中一个失败，确认第二个没有第一个或 HTTP 请求的 context。
- 在日志序列化输出中搜索测试注入的 email、JWT、UUID、参数和异常文本，均不得命中。

## Review Gate

审核 signal 连接位置、允许字段、终态清理和所有禁止字段测试后，才可 `task.py start`。不得将本任务扩展为任务业务重构。
