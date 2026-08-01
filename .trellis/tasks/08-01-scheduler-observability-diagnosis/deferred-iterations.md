# Scheduler Observability Deferred Iterations

## Purpose

当前迭代只恢复 PM2 stdout 收集并实现 structlog JSON 内的详细错误记录。确认的 Sentry 删除单独追踪，
不得扩展当前验收范围。

## Traceability Rules

- 延期项不影响当前任务的验收。
- 实施延期项前必须创建独立 Trellis 任务并完成其 PRD、设计、实施与验证计划。
- 延期项的依赖必须在新任务中重新验证。

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | 删除 Sentry DSN 配置、SDK 初始化、scrubber、依赖、ADR-0001 和关联规范 | 用户已确认不再使用 Sentry，但该清理与当前 stdout 错误追踪无关 | 本任务完成后重新核对所有 Sentry 调用与部署环境变量 | 独立 PRD、设计、删除清单、配置/依赖清理、回归测试与文档更新 |

## Suggested Iteration Order

1. 完成当前单流 structlog 错误追踪与 PM2 验证。
2. 创建 D-001 独立任务并删除 Sentry。

## Remaining Work In Current Scope

完成 `design.md`、`implement.md` 与 `e2e-api-tests.md` 中的代码、测试和 PM2 验证；不执行 D-001。
