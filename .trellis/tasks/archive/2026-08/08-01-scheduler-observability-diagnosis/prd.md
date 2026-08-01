# 排查并完善定时任务日志可观测性

## Goal

恢复 PM2 对 worker stdout 的采集，并让 HTTP 未处理 5xx 与 Celery `FAILURE` 在同一
structlog NDJSON 流中保留完整异常和 traceback，供运维排查。

## Confirmed Facts

- `configure_observability()` 使用 `structlog>=25,<27`、`JSONRenderer` 和
  `PrintLoggerFactory(file=sys.stdout)`；`log_event()` 已经通过 structlog 的
  `info`、`warning`、`error` 方法写事件。
- `SchedulerRun` 是调度业务状态的唯一事实来源。成功、跳过、无待重试项和错误分类均应查询
  PostgreSQL，而不是从日志重建。
- 最近已有成功和跳过的调度运行，但 Celery worker/beat 的 PM2 stdout/stderr 文件为 0 字节。Windows
  下 `cmd /c` 只能被 PM2 采集到 shell 自身输出，不能采集 Python/Celery 子进程 stdout；PM2 必须直接
  托管可执行文件。变更可执行文件时，`pm2 reload` 不会替换旧进程，必须删除并按配置重新创建。
- 未处理 HTTP 异常目前只产生没有 traceback 的 `http.request.failed`；Celery 的 `task_postrun`
  对 `FAILURE` 也只产生没有 traceback 的 `task.failed`。
- 当前没有显式返回 5xx 的 `HTTPException` 或 500 `AppError` 子类；HTTP 5xx 详细记录的范围是
  未处理异常，不为正常响应伪造 traceback。

## Confirmed Decisions

- 不引入标准库 logging 作为第二套应用日志框架，也不增加 stderr handler、文件 handler、Sentry
  或任何新的服务/配置。
- stdout 保持唯一输出 sink。普通事件与详细错误都是可解析的 NDJSON，由 PM2 采集；详细错误的
  JSON 仅增加 `exception` 字段。backend/worker/beat 的 PM2 `time` 必须关闭，否则前缀会破坏 JSON。
- 在 `JSONRenderer` 前加入 `format_exc_info`。受限 `log_exception()` 只用于 HTTP 未处理异常和
  Celery `task_failure`，保留已有 request/task context 及完整 traceback。
- Celery 失败改由 `task_failure` 输出一次 `task.failed`（ERROR）；`task_postrun` 只输出成功的
  `task.completed`，并仍在所有终态清理 context，禁止失败重复记录。
- Celery `setup_logging` 只用于阻止默认文本 handler 和 stdout 重定向，确保 structlog 是唯一输出；它不
  引入任何 logger、handler 或 sink。
- HTTP 响应、Celery 失败语义、scheduler 状态机和 `SchedulerRun` 模型均不改变。

## Requirements

- R1: PM2 必须直接托管 Python/Celery 可执行文件并采集应用 stdout；探针不得连接或消费现有 Celery
  broker 队列。
- R2: HTTP 未处理异常输出一条 `http.request.failed` JSON，包含 request correlation、现有 HTTP
  元数据和完整 traceback；响应仍为原有 `detail + request_id` 500 合约。
- R3: 合法应用 Celery 任务失败输出一条 `task.failed` JSON（ERROR），包含 task correlation 和完整
  traceback；任务成功、重试、拒绝、忽略及无效身份维持现有行为。
- R4: 普通 `log_event()` 事件的 schema 和输出保持不变；详细异常只通过受限入口进入 renderer。
- R5: 更新错误处理与日志规范，使“服务端 traceback”成为已实现、可测试的 stdout JSON 能力。

## Acceptance Criteria

- [x] 临时 PM2 探针确认 stdout 被写入其 out log；若失败，定位并修复进程监督链路后重新验证。
- [x] HTTP 未处理异常产生一条可解析 JSON，其中含 `exception`、`request_id`、方法、路由模板、
  500 状态和耗时；客户端响应合约不变。
- [x] Celery `FAILURE` 产生一条可解析 JSON，其中含 `exception`、合法 task ID/name 及 ERROR
  severity；随后成功任务不会继承失败 task context。
- [x] 同一失败不同时留下旧的无 traceback `task.failed` 记录。
- [x] focused tests、backend quality checks、PM2 运行时探针和文档链接均通过。

## Out Of Scope

- 删除 Sentry 配置、SDK、scrubber、依赖或历史 ADR；见 [deferred-iterations.md](deferred-iterations.md)。
- 标准 logger / handler 多 sink 集成；只有出现第三方日志接入、按级别路由或多个输出目的地时才另立任务。
- 修改 scheduler 业务逻辑、`SchedulerRun` 模型、任务参数或 API 响应 schema。

## Planning Artifacts

- [design.md](design.md)
- [implement.md](implement.md)
- [e2e-api-tests.md](e2e-api-tests.md)
- [deferred-iterations.md](deferred-iterations.md)
- [ADR-0002](../../../docs/decisions/ADR-0002-structlog-json-error-traces.md)
