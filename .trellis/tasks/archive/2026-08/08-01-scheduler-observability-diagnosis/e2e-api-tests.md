# 端到端验证

## HTTP 未处理异常

1. 注册临时测试路由并抛出 `RuntimeError("boom")`。
2. 通过 `TestClient(..., raise_server_exceptions=False)` 请求该路由。
3. 断言仍返回 500、`detail="Internal Server Error"` 与 `X-Request-ID`。
4. 捕获 stdout 的唯一 `http.request.failed` JSON，断言 request ID、method、route template、status 500、
   elapsed time 和包含 `RuntimeError: boom` 的 `exception`。

## Celery Failure

1. 注册一个仅用于测试的 eager Celery task，并抛出 `RuntimeError("task boom")`。
2. 使用合法 task ID 执行失败任务，再执行 `runtime.ping` 成功任务。
3. 断言 JSON 顺序为 `task.started`、`task.failed`、`task.started`、`task.completed`。
4. 断言失败事件是 ERROR、带 task ID/name 和 `RuntimeError: task boom` traceback；成功事件不含
   `exception`，且 context 已清理。

## Process And PM2

1. 运行现有 subprocess 生命周期测试，断言 stdout 每行仍是可解析 JSON。
2. 在 PM2 中运行短生命周期 Python stdout probe，断言直接 executable 的 out log 包含完整 NDJSON；
   `cmd /c` 包装不得作为应用启动方式；随后删除 probe。
3. delete/start 重建 worker 并确认 worker PM2 out log 能接收 task 生命周期事件和 `task.failed`
   traceback，PM2 不添加时间前缀且 stderr 没有新增 Celery formatter 前缀；若不通过，先修复进程监督
   链路，再执行这一检查。

## Non-Regression

- 普通成功、4xx、RETRY、REJECTED、IGNORED 与无效 task identity 不出现 `exception`。
- API error body/OpenAPI/frontend generated client 均不改变。
