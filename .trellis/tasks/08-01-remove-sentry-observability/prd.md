# 删除 Sentry 可观测性集成

## Goal

从应用运行时、受版本控制的配置、部署流程、依赖和现行决策/规范中移除 Sentry，保留唯一的
structlog stdout NDJSON 可观测性通道。

## Confirmed Facts

- 本任务源自归档任务 `08-01-scheduler-observability-diagnosis` 的延期项 D-001；当时只恢复了
  structlog JSON 错误追踪，未删除 Sentry。
- `backend/app/main.py` 包含 SDK 初始化、错误/事务 scrubber、Sentry 类型与 trace-ID 正则；
  `backend/app/core/config.py` 定义 `SENTRY_DSN`；测试仍直接导入并验证 scrubber。
- `backend/pyproject.toml` 声明 `sentry-sdk[fastapi]`，顶层 `uv.lock` 锁定它。
- `.env`、`.env.production.example`、`compose.yml`、两份部署工作流、`copier.yml`、README 和
  deployment 文档仍传递或说明 `SENTRY_DSN`。
- ADR-0001 与现行 logging 指南仍规定 Sentry 契约；ADR-0002、架构分析和企业脚手架评估仍把
  Sentry 描述为当前或已弃用的能力。
- 归档 Trellis 任务、开发日志和历史变更记录中的 Sentry 叙述必须保留，不作为当前能力说明。

## Requirements

- R-001：删除 SDK 初始化、scrubber、仅服务于它们的类型/正则和对应测试；应用入口、路由与
  structlog 初始化行为保持不变。
- R-002：删除 `SENTRY_DSN` 设置和所有受版本控制的环境传递点，包括 `.env`、生产示例、
  Compose 四个服务、Copier 输入及 staging/production 部署工作流。
- R-003：从项目依赖和锁文件移除 `sentry-sdk`，使用项目既有 `uv` 重新生成锁文件。
- R-004：删除 ADR-0001；从 ADR-0002、现行 logging 规范、架构/能力评估、README 与部署文档
  删除把 Sentry 表述为可用、要求或替代方案的内容，同时保留 structlog stdout NDJSON 决策。
- R-005：保留归档 Trellis 任务、开发日志和历史变更记录中的 Sentry 叙述，不做全仓批量替换。
- R-006：合并并成功部署后，删除 GitHub Actions 仓库/环境 secret 与实际部署环境中的
  `SENTRY_DSN`。

## Acceptance Criteria

- [x] AC-001：`backend/app/main.py`、`backend/app/core/config.py` 和相关测试不再导入、配置或
  调用 Sentry；现有 FastAPI 导入探针继续通过。
- [x] AC-002：`.env`、`.env.production.example`、`compose.yml`、`copier.yml` 和
  staging/production 工作流不再定义、插值或传递 `SENTRY_DSN`。
- [x] AC-003：`backend/pyproject.toml` 和由 `uv` 生成的 `uv.lock` 不再包含 `sentry-sdk`。
- [x] AC-004：ADR-0001 已删除；ADR-0002、现行 logging 指南、架构/能力评估、README 和
  deployment 文档不再将 Sentry 表述为当前能力或选择。
- [x] AC-005：归档 Trellis 任务、开发日志和历史变更记录保持不变；删除范围仅限现行运行、部署
  与规范资料。
- [x] AC-006：后端 focused tests、格式化、静态检查、锁文件检查和无 `SENTRY_DSN` 的健康检查
  通过，且不产生持久化副作用。
- [ ] AC-007：合并后的发布检查记录已确认 GitHub Actions 和实际部署环境不再保留
  `SENTRY_DSN`。

## Out Of Scope

- 新增第三方错误追踪服务、日志 sink、stderr 输出或标准库 logging 管道。
- 重构 structlog schema、HTTP/Celery 错误追踪逻辑、PM2 配置或 API 合约。
- 修改归档 Trellis 任务、开发日志和历史变更记录。
