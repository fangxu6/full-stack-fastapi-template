# 请求级 Unit of Work

## Goal

为每个 HTTP 写请求提供唯一的数据库事务边界：endpoint 成功后提交，任何异常后回滚。业务服务、CRUD 和路由不再各自决定最终事务结果。

## Confirmed Facts

- `backend/app/api/dependencies/database.py` 的 `get_db()` 当前仅创建并关闭 `Session`，没有提交或回滚语义。
- 用户、IAM、库存、scheduler、items 和 private 路由的写路径，以及部分 CRUD/服务，仍直接调用 `session.commit()` 或 `session.rollback()`。
- Celery worker、库存日报、导入器、启动初始化和 Alembic 不是 HTTP 请求，必须保留各自显式的短事务。
- 调度手工运行在提交后由现有每分钟 scanner 投递；HTTP 路径不能在事务提交前直接发布 Celery 消息。

## Requirements

1. 新增 `WriteSessionDep`，复用请求缓存的 `get_db` Session；endpoint 正常完成后提交，任何异常路径回滚并继续抛出原异常。
2. 保留 `SessionDep` 作为读会话依赖。所有 HTTP `POST`、`PUT`、`PATCH`、`DELETE` 使用 `WriteSessionDep`，包括当前只认证或读取的写方法。
3. HTTP 写服务、CRUD 和路由可以 `add`、`flush`、`refresh` 和转换完整性错误，但不得调用 `commit()` 或 `rollback()`。
4. 对 HTTP 外直接调用的服务，先在调用方建立明确事务所有者，再移除内部事务终结调用；不得把 worker、CLI、启动、导入或迁移强行接入 HTTP 依赖。
5. 一次请求内的业务行、审计行和将来的 outbox 行必须同事务提交或回滚；不得以提前发送 Celery 消息替代提交后调度扫描。

## Acceptance Criteria

- [ ] 所有 HTTP 写路由均使用 `WriteSessionDep`；读取路由和认证依赖继续使用 `SessionDep`。
- [ ] endpoint 成功时只发生一次最终提交；endpoint、依赖或服务抛出异常时回滚且无局部持久化。
- [ ] HTTP 路径中的服务、CRUD 和路由不再调用 `session.commit()`/`session.rollback()`。
- [ ] 非 HTTP 任务保留显式短事务，并且没有数据库事务跨 SMTP、HTTP 或 Celery broker 调用。
- [ ] 用户、IAM、库存、scheduler、items、private 与登录相关写路径的现有 API 回归通过。

## Out Of Scope

- 不新增通用 Repository、UnitOfWork 类、事务装饰器或全局事务中间件。
- 不改造 Celery 任务、导入器、日报投递或迁移的事务实现；只确保它们在移除服务层 commit 后仍有明确 owner。
- 不实现 System Actor、outbox 或 Celery 日志上下文；这些由后续子任务处理。

## Dependencies

- 前置：无。
- 后续：`07-27-explicit-audit-actor` 与 `07-27-generic-email-outbox` 依赖此任务提供的 HTTP 原子提交边界。
- 决策依据：`docs/adr/0006-use-request-scoped-unit-of-work-for-http-writes.md`。
