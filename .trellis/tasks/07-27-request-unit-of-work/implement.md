# Implementation Plan

1. 以 `research/fastapi-function-scope-evidence.md` 的 38 条 handler 清单为基线，列出每个 handler 调用的 service/CRUD 及其非 HTTP 调用者。
2. 在数据库依赖模块增加 function-scope `get_write_db()`/`WriteSessionDep`，其子依赖直接声明同一 function-scope `get_db`；在认证模块将全局 `SessionDep` 设为相同 callable/scope，测试读/认证/RBAC/写依赖复用同一 Session 且无导入环。
3. 先迁移 items、private、users、login、utils；将 CRUD 的 `commit` 参数和 service 的 commit/rollback 删除或收敛为 flush/refresh，保留 HTTP 错误语义。
4. 迁移 IAM、inventory、scheduler 路由与服务；对完整性错误在 endpoint 返回前的 `flush()` 时转换为既有领域错误，交由 WriteSessionDep 统一回滚，避免可预期 409 在 response 生成后才发生。
5. 为 `crud.authenticate`、`init_db`、inventory importer、inventory daily report、scheduler worker/scan/cleanup 等 HTTP 外调用者保留或补上显式短事务 owner；任何外部操作都在提交后发生。
6. 检查手工 scheduler run 仍仅提交 `QUEUED` record，现有 scanner 再投递；全量搜索 HTTP 路径的 `commit()`/`rollback()`，运行质量检查和 E2E 用例。

## Validation

- `python -m pytest backend/tests/api backend/tests/services backend/tests/crud`
- `rg -n "session\.(commit|rollback)\(" backend/app/api backend/app/services backend/app/crud backend/app/modules`
- 为读、认证/RBAC 和每个迁移的 HTTP handler 验证：所有 Session 依赖 teardown 在响应发送前完成、失败可转成现有错误响应、认证/权限与写依赖共享 Session。
- 对隔离测试库执行成功写入和失败写入，验证事务原子性。

## Review Gate

在 `task.py start` 前审核 38 条 HTTP 写路由清单、function-scope Session 共享测试及仍保留 commit/rollback 的非 HTTP 理由。此任务不创建迁移或前端变更。
