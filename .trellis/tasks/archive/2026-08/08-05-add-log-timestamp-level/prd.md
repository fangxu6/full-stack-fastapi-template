# 统一日志前缀时间与等级

## Goal

让每条后端日志在 JSON 对象开头显示时间和日志等级，同时保持现有结构化日志采集契约。

## Confirmed Facts

- 应用日志由 `backend/app/core/observability.py` 中的 structlog 配置写入 stdout。
- 当前格式是每行一个可解析的 NDJSON JSON 对象；`timestamp` 已由 `TimeStamper` 生成 ISO UTC 时间，`severity` 已由日志 facade 写入。
- 日志由 `JSONRenderer` 序列化，`log_event()` 和 `log_exception()` 共用同一输出入口。

## Requirements

- R1: 将 `timestamp` 和 `severity` 作为 JSON 对象的前两个字段输出，顺序固定为时间、等级。
- R2: 保留现有日志事件字段、值、调用方式、stdout sink 和单行 JSON 格式；不在 JSON 外增加文本前缀。
- R3: 普通事件和受限异常事件均使用相同的字段排序规则。

## Acceptance Criteria

- [x] 普通日志原始行的前两个 JSON 字段依次为 `timestamp`、`severity`，且时间为现有 ISO UTC 格式。
- [x] 异常日志原始行的前两个 JSON 字段依次为 `timestamp`、`severity`，并继续包含现有异常字段。
- [x] 现有日志相关测试和新增格式测试通过；输出仍可由 `json.loads` 解析。
- [x] 后端 lint、类型检查和格式检查通过。

## Out Of Scope

- 不新增标准库 logger、handler、文件 sink、外部日志平台配置或 PM2 文本时间前缀。
- 不修改业务日志调用、事件 schema、日志采集方式或日志保留策略。
