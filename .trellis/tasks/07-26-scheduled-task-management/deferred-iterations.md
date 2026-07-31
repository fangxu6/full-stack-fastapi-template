# 定时任务管理系统 Deferred Iterations

## Purpose

本期只提供单个 Cron 计划、通用人工运行和服务端 Cron 校验。以下已确认的后续能力在
单独任务中规划，不影响本期验收。

## Traceability Rules

- 延后项不构成本期验收标准。
- 每项实施前必须创建独立任务，并补齐 PRD、设计、API 与测试计划。
- 不在本期 UI 或 API 中暴露占位入口。

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
|---|---|---|---|---|
| D-001 | 逐实现类限制立即运行或历史补发 | 首期全部实现类默认支持，避免增加基类与配置认知负担 | 本期任务定义与运行模型 | 独立 PRD、配置契约、API、UI 与测试 |
| D-002 | Cron 后续执行时点预览 | 本期仅需服务端保存校验与 `next_run_at` | 本期 Cron 解析器与管理 API | 只读预览 API、管理页与时区测试 |
| D-003 | 超过 90 天的历史补发 | 首期窗口与运行快照保留期对齐，限制误操作范围 | 本期单时点补发 API | 业务授权规则、容量验证与测试 |

## Suggested Iteration Order

- D-001、D-002 和 D-003 的本期依赖已完成，后续均可独立创建任务并规划实施。

## Completion Status

- 本期定时任务管理功能已由 `c8175af` 实现，并在 `75ea147` 和 `8a3abbf` 完成审查修复及
  投递租约补强；修复子任务已于 2026-07-27 归档。
- D-001、D-002 和 D-003 仍未创建为独立任务，继续处于延后状态，不构成本期遗漏或验收阻塞。
