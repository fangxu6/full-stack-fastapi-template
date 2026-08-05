# 格式化 PM2 结构化日志前缀

## Goal

让 PM2 托管的后端/Celery stdout 在原始 NDJSON 前显示前七个 JSON 字段值并用竖线分隔，保留原始 JSON。

## Confirmed Facts

- PM2 当前直接托管 Python/Celery 可执行文件，并在 stdout 行前添加进程编号和名称。
- PM2 自身不能解析 JSON 字段；应用已经输出带固定顺序元数据的单行 NDJSON。
- PM2 的 `time` 保持关闭，避免破坏 stdout 文件的原始 NDJSON；本次只改变 PM2 终端/输出行的展示包装。

## Requirements

- R1: 后端、Celery worker 和 Celery beat 由一个 Node 标准库包装器启动；子进程命令、工作目录、环境变量和退出码语义保持不变。
- R2: 包装器遇到 JSON 对象时，取其当前顺序的前七个字段值，用 ` | ` 连接并放在原始 JSON 前；最终由 PM2 显示为 `process | value1 | ... | value7 | {json}`。
- R3: 非 JSON stdout 行和全部 stderr 原样透传；包装器异常或子进程退出必须能让 PM2 感知并重启。
- R4: 不修改应用 NDJSON 内容，不改变 PM2 的进程名称、`time` 设置和 frontend 配置。

## Acceptance Criteria

- [x] 包装器对完整 JSON 行输出七个竖线分隔值和原始 JSON，对非 JSON 行原样输出。
- [x] backend、worker、beat 的 PM2 配置均通过包装器启动，frontend 配置保持不变。
- [x] 包装器转发子进程 stdout/stderr、信号和退出码，不遗留子进程。
- [x] 包装器单元测试、配置静态检查和 PM2 配置加载验证通过。

## Out Of Scope

- 不修改应用日志字段、JSON schema、日志采集平台或 PM2 自身源码。
- 不格式化 PM2 error log 中的 Python warning/traceback 文本。
