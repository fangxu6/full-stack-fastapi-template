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
| One-time cleanup workflow | 新增 `workflow_dispatch` 工作流；固定 `SENTRY_DSN`，在指定 self-hosted environment runner 上验证容器和 backend 健康后，删除 environment/repository secret | 不读取或显示 secret 值；不接受任意 secret、路径或命令输入 |
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

代码合并前只移除 workflow 对 secret 的引用，不能删除外部 secret。合并后，以一次性
`workflow_dispatch` 在 `staging` 和 `production` 各执行一次：job 使用同名 GitHub Environment
与标签匹配的 self-hosted runner，固定检查 `backend`、`celery-worker`、`celery-beat` 三个运行
容器均没有 `SENTRY_DSN`，再从 backend 容器调用本地健康端点。两项验证成功后，job 以最小
`actions: write` 权限删除该 environment 和 repository 范围的同名 secret；`204` 与“不存在”的
`404` 都是可记录的完成结果，其他状态失败退出。执行日志只写环境名、容器服务名、HTTP 状态与
结果，不写 secret 值。两环境都成功后，由常规源代码提交删除该一次性工作流，工作流不自删。

若必须回滚到旧镜像，缺少该可选变量只会让旧 Sentry 初始化不执行，不会阻止应用启动；不恢复
secret。

## Trade-offs

删除历史叙述会降低检索噪声，但会破坏决策链，因此明确不做。保留任何运行时兼容层会让一个已停用
的集成继续成为维护面，故不保留。一次性工作流的写权限只为删除外部配置所需；它不接受输入的
secret 名称或 shell 命令，并在任务完成后删除，避免形成长期的通用 secret 管理面。
