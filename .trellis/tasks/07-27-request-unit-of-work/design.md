# Technical Design

## Boundary

`get_db()` 继续是请求缓存的 Session 来源。新增生成器依赖 `get_write_db()` 并导出 `WriteSessionDep`：在 `yield` 返回后提交，捕获任何异常时回滚并重新抛出，最后由 `get_db()` 关闭同一 Session。FastAPI 的依赖缓存保证认证依赖与写依赖观察到同一会话。

`SessionDep` 不改变，避免把读请求、认证读取和外部入口引入提交语义。HTTP 写 endpoint 仅声明 `WriteSessionDep`；服务和 CRUD 以 `flush()` 获取 ID 或捕获约束错误，以 `refresh()` 返回已写状态，但不终结事务。

## Migration Scope

1. 增加共享依赖及其单元测试。
2. 枚举并迁移 API 路由中的 `POST`、`PUT`、`PATCH`、`DELETE`：用户、登录、items、private、IAM、inventory、scheduler。
3. 移除仅由 HTTP 调用的服务/CRUD 的 commit/rollback；对仍被 worker、CLI、导入或启动调用的函数，先改为由外部调用者显式提交。
4. 检查任务投递：HTTP 不直接 `.delay()`；需要异步执行的 scheduler run 保持持久化 `QUEUED`，由 scanner 在提交后投递。

## Failure And Rollback

- 业务、验证或完整性异常穿透依赖，Unit of Work 回滚所有本请求新增/更新状态。
- 依赖创建失败时不尝试提交；关闭 Session 仍由 `get_db()` 管理。
- 不在数据库事务内调用 SMTP、外部 HTTP 或 broker；外部操作留给异步边界。
- 无 schema 变化；回滚为恢复单个已迁移 HTTP 模块的原依赖和服务提交调用，不影响非 HTTP 事务。
