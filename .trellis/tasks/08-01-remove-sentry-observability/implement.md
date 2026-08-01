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

- 确认 staging 与 production 部署工作流成功，健康检查通过后，删除 GitHub Actions repository /
  environment 的 `SENTRY_DSN` secret。
- 从实际部署环境（包括运行节点或其配置管理）删除 `SENTRY_DSN`，重启或滚动部署后复查健康检查。
- 将外部 secret/环境变量删除的执行结果记录到任务验证说明；未完成前不将 AC-007 标记完成。

## Risk And Rollback

- 依赖锁定只能通过 `uv` 生成；若解析导致无关升级，恢复该锁文件并以当前 lock 重新解析。
- 文档清理不可按搜索结果全量删除，必须保留已指定的历史资料。
- 回滚旧应用版本不需要恢复 `SENTRY_DSN`，因为该变量对旧版本也是可选的；Sentry 只会保持停用。
