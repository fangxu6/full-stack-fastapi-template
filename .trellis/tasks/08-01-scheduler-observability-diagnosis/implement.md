# 实施计划

## 1. 先验证运行时输出链路

- 使用短生命周期、无 broker 的 Python stdout probe 对比 PM2 直接 executable 与 `cmd /c` 包装。
- 读取该 probe 的 PM2 out/error log，立即删除 probe。
- 直接 executable 通过后，更新 `ecosystem.config.js` 的 backend/worker/beat；对 Celery 命令使用全局
  `-q`，并用 delete/start 应用 executable 变更，不要用 reload。

## 2. 实现单流详细错误事件

- 在 `backend/app/core/observability.py` 插入 `format_exc_info`，并实现受限 `log_exception()`。
- 在 `backend/app/core/exceptions.py` 的未处理异常分支调用它，保留现有 HTTP metadata 与重新抛出行为。
- 在 `backend/app/core/celery.py` 监听 `task_failure`，以当前 context 记录失败；将 postrun 限制为成功
  终态事件和 context 清理，并注册 `setup_logging` receiver 保留 structlog stdout。

## 3. 更新可执行契约与测试

- 更新 `.trellis/spec/backend/logging-guidelines.md` 与 `error-handling.md`，删除与详细异常 JSON 冲突的
  禁令，保留普通事件不含异常的边界。
- 更新 observability、HTTP exception、Celery lifecycle 测试，并保留现有 eager/subprocess 输出覆盖。
- 更新 ADR/AI changelog 引用；不修改 Sentry 代码或配置，删除工作见
  [deferred-iterations.md](deferred-iterations.md)。

## 4. 验证与回归

- 运行 focused pytest，再运行 `uv run ruff check app`、`uv run ty check app`、`uv run mypy app` 和
  backend quality hook。
- 重启受影响 PM2 进程后，确认 worker/beat/backend online；使用可控失败场景验证 out log 为 NDJSON
  且包含 traceback。

## Risk Points

- `task_failure` 必须在 `task_postrun` 清理 context 前记录异常，且同一失败不能双写。
- 日志写入继续 best effort；记录失败不得覆盖原始 HTTP 或 Celery 异常。
- PM2 probe 只能使用临时独立进程，不能连接 Redis 或执行业务任务。
