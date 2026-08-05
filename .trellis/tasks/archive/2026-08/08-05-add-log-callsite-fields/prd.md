# 为 NDJSON 日志追加调用位置

## Goal

在 `timestamp` 和 `severity` 后追加实际日志调用者的完整限定路径及代码行号，保持单行 NDJSON。

## Confirmed Facts

- 应用日志统一经过 `backend/app/core/observability.py` 的 `log_event()` 或 `log_exception()`，再由 structlog 写入 stdout。
- 当前日志已将 `timestamp`、`severity` 排在 JSON 对象开头；本次只在其后增加调用位置字段，不改 PM2 配置。
- structlog 的 `CallsiteParameterAdder` 可以忽略日志 facade 的栈帧，取得实际业务调用者的模块、限定名和行号。

## Requirements

- R1: 每条普通事件和受限异常事件都包含 `source` 和 `line` 字段。
- R2: `source` 使用模块名和调用者限定名组成的完整路径，例如 `app.modules.scheduler.tasks.scan_due_jobs` 或 `app.services.UserService.create`；`line` 使用发起日志调用的源代码行号。
- R3: JSON 字段顺序固定为 `timestamp`、`severity`、`source`、`line`，然后保留现有字段和值。
- R4: 保持 stdout 单行 JSON、现有 logger facade、事件 schema 语义和 PM2 配置不变。

## Acceptance Criteria

- [x] 普通日志包含正确的 `source` 和 `line`，且前四个 JSON 字段依次为 `timestamp`、`severity`、`source`、`line`。
- [x] 异常日志包含实际异常调用点的 `source` 和 `line`，并继续保留 traceback 字段。
- [x] Celery、HTTP、startup、dependency 和 cache 日志均通过共享入口生成位置字段。
- [x] 现有日志相关测试、新增调用位置测试、后端 lint/type/Ruff 检查通过。

## Out Of Scope

- 不改变 PM2 的 `time`、进程前缀或日志展示格式。
- 不在 JSON 外添加文本前缀，不新增第二套日志框架或日志 sink。
