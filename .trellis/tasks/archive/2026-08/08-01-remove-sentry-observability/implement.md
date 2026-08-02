# 实施计划

## 1. 建立删除清单并保护历史边界

- 以 `rg -n -i sentry` 记录当前命中；将运行时、受版本控制配置、现行文档与历史记录分组。
- 仅修改本计划列出的活动文件；不修改 `.trellis/tasks/archive/`、
  `docs/decisions/AI_CHANGELOG.md` 或 `.trellis/spec/log.md`。

## 2. 删除应用集成和专属测试

- 从 `backend/app/main.py` 删除 SDK 依赖、Sentry 初始化及 scrubber 辅助代码；保留
  `configure_observability()` 与现有 FastAPI 构造顺序。
- 从 `backend/app/core/config.py` 删除 `HttpUrl` import（若已无其他使用）与 `SENTRY_DSN`。
- 从 `backend/tests/core/test_observability.py` 删除 SDK 类型 import 和两个 scrubber 测试。
- 保留 `backend/tests/core/test_celery.py` 的既有 subprocess import probe；不为已删除的配置新增
  重复启动测试。

## 3. 删除受版本控制的配置和依赖

- 从 `.env`、`.env.production.example`、`copier.yml`、`compose.yml` 的
  prestart/backend/celery-worker/celery-beat 环境列表，以及两个部署工作流的 job `env` 删除
  `SENTRY_DSN`。
- 从 `backend/pyproject.toml` 删除 `sentry-sdk[fastapi]` 及会传递引入它的
  `fastapi[standard]` extra；声明已有运行时所需的 `fastapi` 与 `uvicorn[standard]`，执行
  `uv lock --project backend`；审阅 `uv.lock` 只移除 Sentry/CLI 链路及
  不再被引用的传递依赖，不接受无关升级。

## 4. 清理现行文档

- 删除 `docs/decisions/ADR-0001-internal-sentry-trace-correlation.md`。
- 更新 ADR-0002、`.trellis/spec/backend/logging-guidelines.md`、架构分析、企业脚手架评估、
  `README.md` 和 `deployment.md`，移除活跃 Sentry 契约、链接、示例和变量说明；保留 structlog
  stdout NDJSON 的现行说明。
- 再次检查范围，确认历史记录只作为剩余命中保留。

## 5. 验证

- 执行 focused backend tests：`uv run pytest tests/core/test_observability.py tests/core/test_celery.py`
  和健康检查覆盖所在的 API 测试模块。
- 在 `backend/` 执行 `uv run ruff check app tests`、`uv run ruff format --check app tests`、
  `uv run mypy app tests` 与 `uv run ty check app`；执行
  `uv lock --project backend --check`。
- 使用不含 `SENTRY_DSN` 的已启动本地 backend 调用
  `http://127.0.0.1:8000/api/v1/utils/health-check/`；记录响应和无持久化副作用。
- 使用 `git diff --check` 与范围化 `rg` 审阅，确认当前运行/部署/规范资料无遗留，历史命中未修改。

## 6. 合并后发布检查

- 新增仅含 `workflow_dispatch` 的 `.github/workflows/remove-sentry-observability.yml`。输入为受
  限的 `staging`/`production` 选择；job 绑定该 GitHub Environment，并运行在匹配的 self-hosted
  runner。
- 不 checkout 源码、不接受 secret 名称、路径或命令输入。以固定 `SENTRY_DSN` 和最小
  `actions: write` 的 `GITHUB_TOKEN` 调用 GitHub REST API；先验证运行中的 backend、worker、beat
  容器不含该变量，并从 backend 容器调用本地健康端点，再删除 environment/repository scope。
- 静态校验 YAML 与 workflow 的输入、权限、runner 标签、固定变量名和 API 路径；推送默认分支后
  从 Actions 页面分别手动执行 staging、production。只有两次均完成且日志不含值时才标记
  AC-007/AC-008 完成。
- 以常规提交删除这份一次性工作流，并将两次运行 URL 与删除结果记录到任务验证说明；未完成前
  不归档任务。

## Risk And Rollback

- 依赖锁定只能通过 `uv` 生成；若解析导致无关升级，恢复该锁文件并以当前 lock 重新解析。
- 文档清理不可按搜索结果全量删除，必须保留已指定的历史资料。
- 回滚旧应用版本不需要恢复 `SENTRY_DSN`，因为该变量对旧版本也是可选的；Sentry 只会保持停用。
