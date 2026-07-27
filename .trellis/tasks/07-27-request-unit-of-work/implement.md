# Implementation Plan

1. 列出所有 HTTP 写路由及其服务/CRUD 调用链，区分 HTTP 与非 HTTP 调用者。
2. 在数据库依赖模块增加 `get_write_db()`/`WriteSessionDep`，为成功、异常和 Session 复用编写最小测试。
3. 逐模块迁移路由依赖并移除服务、CRUD、路由的事务终结调用；每个模块后运行其 API 回归。
4. 为外部调用者保留或补上显式短事务 owner，检查无 HTTP endpoint 在 commit 前发布任务。
5. 全量搜索 HTTP 相关路径的 `commit()`/`rollback()`，运行后端质量检查和 E2E 用例。

## Validation

- `python -m pytest backend/tests/api backend/tests/services backend/tests/crud`
- `rg -n "session\.(commit|rollback)\(" backend/app/api backend/app/services backend/app/crud backend/app/modules`
- 对隔离测试库执行成功写入和失败写入，验证事务原子性。

## Review Gate

在 `task.py start` 前审核所有 HTTP 写路由清单及仍保留 commit/rollback 的非 HTTP 理由。此任务不创建迁移或前端变更。
