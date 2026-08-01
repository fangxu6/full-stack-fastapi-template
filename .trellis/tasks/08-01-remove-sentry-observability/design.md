# 技术设计

## Decision

删除整条 Sentry 集成链路，不用 feature flag 或替代 transport。当前唯一应用日志路径已经是
`structlog -> stdout NDJSON`；移除 Sentry 不改变这一条路径，也不改变 HTTP、Celery 或 API
响应行为。

## Boundaries

| Boundary | Change | Preserve |
| --- | --- | --- |
| Application | 从 `backend/app/main.py` 删除 SDK import/init、scrubber、trace-ID matcher 和仅供它们使用的辅助函数；从 Settings 删除 `SENTRY_DSN` | FastAPI app 构建、异常处理、请求 ID 和 `configure_observability()` |
| Tests | 删除 scrubber 的类型 import 与两个专属测试；保留现有 FastAPI subprocess import probe | 现有 structlog、HTTP 和 Celery 回归测试 |
| Dependencies | 删除直接 SDK 依赖及会传递引入它的 `fastapi[standard]` extra；以显式 `fastapi` 和现有运行时 `uvicorn[standard]` 替代，再用 `uv lock --project backend` 更新顶层锁文件 | Uvicorn server/reload 能力与其余锁定版本，不执行升级 |
| Versioned delivery config | 从 `.env`、`.env.production.example`、`copier.yml`、Compose 的 prestart/backend/worker/beat 和两份部署工作流删除变量 | 其余环境变量及部署步骤 |
| Current documentation | 删除 ADR-0001；从 ADR-0002、logging 指南、架构/能力评估、README 和 deployment 文档删除 Sentry 能力说明、替代方案和链接 | structlog stdout NDJSON 的现行约束 |
| Historical record | 不改归档任务、`docs/decisions/AI_CHANGELOG.md`、`.trellis/spec/log.md` 或其他历史记录 | 已发生决策的可追溯性 |

## Runtime Contract

移除后，设置模型不再接受或暴露 `SENTRY_DSN`，应用入口没有第三方 telemetry 初始化。
未设置该环境变量的进程仍按现有必填环境变量初始化 FastAPI，并仅通过 structlog 向 stdout
写入 JSON。旧部署镜像即使变量已被删除也能启动，因为此前该字段本来就是可选的。

## Documentation Contract

ADR-0001 是已废弃集成的唯一专属决策，直接删除。ADR-0002 仍是当前的错误追踪决策，因此保留
文件但删除其 Sentry 替代方案、D-001 follow-up 和 ADR-0001 链接。现行规范只描述 structlog
行为；带日期的 changelog、spec log 和归档任务不重写。

## Deployment And Rollback

代码合并前只移除 workflow 对 secret 的引用，不能删除外部 secret。合并并确认新镜像健康后，
运维删除 GitHub Actions staging/production environment 或 repository 中的 `SENTRY_DSN` secret，
并从实际部署环境删除同名变量。若必须回滚到旧镜像，缺少该可选变量只会让旧 Sentry 初始化不执行，
不会阻止应用启动；不恢复 secret。

## Trade-offs

删除历史叙述会降低检索噪声，但会破坏决策链，因此明确不做。保留任何运行时兼容层会让一个已停用
的集成继续成为维护面，故不保留。
