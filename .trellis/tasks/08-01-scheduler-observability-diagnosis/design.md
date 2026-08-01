# 单一 Structlog 错误流设计

## Boundary

structlog 是唯一应用日志 API，stdout 是唯一 sink。`PrintLoggerFactory(file=sys.stdout)` 保持不变；
PM2 负责接收进程输出。标准库 logging 只保留现有 root/Uvicorn 抑制用途，不能作为第二套应用日志
管道。

`log_event()` 继续产生普通运行事件。`log_exception()` 是同一模块中的受限补充入口，只接受
`http.request.failed` 或 `task.failed`、原始异常和已审核的关联元数据；它调用同一 structlog logger，
不创建 logger、handler 或输出文件。

Celery 在应用导入时注册 `setup_logging` receiver。receiver 的存在会跳过 Celery 默认 logging setup，
从而避免文本 formatter 或 stdout 重定向污染 JSON 流；worker/beat 的 `-q` 单独关闭直接打印的 banner。
它不建立第二套日志 API。

## Event Rendering

`configure_observability()` 在 `JSONRenderer` 前插入 `structlog.processors.format_exc_info`。
只有 `log_exception()` 会传递 `exc_info`，因此普通事件不会获得 `exception` 字段。详细错误仍为一行
JSON，完整 traceback 位于 `exception` 字段，PM2 不需要了解 Python 的文本 formatter。

## HTTP Flow

`RequestIdMiddleware` 已在请求入口绑定 request context。在其 `except Exception as exc` 分支中：

1. 计算原有 elapsed time、method、route template 和 500 status。
2. 调用 `log_exception(event_name="http.request.failed", exception=exc, ...)`。
3. 原样重新抛出异常，让现有全局 handler 返回原有 `detail + request_id` JSON。
4. `finally` 清理 request context。

每个未处理异常只产生这一条失败记录。显式业务 4xx、验证错误和正常响应不进入详细错误路径。

## Celery Flow

`task_prerun` 继续验证并绑定 task ID/name，然后输出 `task.started`。Celery 在错误处理范围内发送
`task_failure`，其中带有异常与 traceback；新的 receiver 在已有 context 存在时调用
`log_exception(event_name="task.failed", exception=..., traceback=...)`，输出 ERROR 记录。

`task_postrun` 只在 `SUCCESS` 时输出 `task.completed`，并在 `finally` 中清理 context。它不再为
`FAILURE` 输出事件，从而没有重复失败记录。`RETRY`、`REJECTED`、`IGNORED`、无效 task identity
保持无终态事件的现有契约。

## PM2 Verification

短生命周期、无 broker 依赖的 Python probe 证明 PM2 直接托管可执行文件时可收集一行 NDJSON；同一
probe 经 `cmd /c` 包装时没有 Python 输出。`ecosystem.config.js` 因而直接运行 backend Python 与
Celery executable，并对 backend/worker/beat 关闭 PM2 `time` 前缀以保持每行有效 JSON。Celery worker
和 beat 使用全局 `-q` 关闭绕过 logging 的 banner print。PM2 必须删除并重新创建应用才会替换 Windows
进程 executable，不能用 reload。

## Compatibility And Rollback

HTTP response、Celery 任务执行与数据库状态不变。回滚只需移除 `format_exc_info` 和异常 receiver/
调用点，恢复 `task_postrun` 的 FAILURE 事件映射；PM2 进程配置和 Celery logging receiver 均由本次
probe 证明必要。

Sentry 删除是独立延期项，不构成本任务验收；见
[deferred-iterations.md](deferred-iterations.md)。
