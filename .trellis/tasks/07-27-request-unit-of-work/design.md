# Technical Design

## Boundary

`get_db()` 继续是请求缓存的 Session 来源，但 `SessionDep` 必须显式声明 `Depends(get_db, scope="function")`。数据库依赖模块新增 `get_write_db()` 并导出同为 function-scope 的 `WriteSessionDep`；它直接依赖相同 callable/scope 的 `get_db`，而不是导入认证模块的 `SessionDep`，避免循环导入。在 `yield` 返回后它提交，捕获任何异常时回滚并重新抛出，最后由 `get_db()` 关闭同一 Session。FastAPI 的依赖缓存只有在 callable 和 scope 均一致时才保证认证、权限与写依赖观察到同一会话。

`SessionDep` 仍无提交语义，只改变其 HTTP function-scope 生命周期；这让读请求、认证读取和写请求都在响应生成前关闭 Session。HTTP 写 endpoint 仅声明 `WriteSessionDep`；认证/权限子依赖继续声明 `SessionDep` 并共用该 Session。服务和 CRUD 以 `flush()` 获取 ID 或捕获约束错误，以 `refresh()` 返回已写状态，但不终结事务。对于必须维持 `409` 等领域错误的约束冲突，服务应在返回 endpoint 前 `flush()` 并转换错误，不能把可预期的完整性错误留到最终 commit。

`SessionDep` 的 function scope 是全局 HTTP 决策，不仅限于写路由。当前应用没有流式 endpoint 或响应发送后继续访问 Session 的路径；未来新增此类 endpoint 时，必须显式评估其依赖 scope，不能悄然把共享 `SessionDep` 改回 request scope。

## Verified Route Inventory

| Module | Write handlers | Notes |
| --- | ---: | --- |
| items | 3 | create, update, delete |
| login | 5 | 包含 access-token、test-token 和 recovery HTML 等当前无写或条件写 POST |
| private | 1 | local-only user creation |
| users | 7 | create, self update/password/delete, signup, managed update/delete |
| utils | 1 | test email；后续 outbox 子任务会改变其业务副作用 |
| IAM | 5 | role CRUD、权限替换、用户角色替换 |
| inventory | 8 | 单位、单据、删除与恢复 |
| scheduler | 8 | job CRUD、启停、restore、run-now、backfill |

所有上述 handler 都迁移到 `WriteSessionDep`。不以“当前没有 DB 变更”为由保留 request-scope SessionDep，因为 ADR-0006 将 HTTP 写方法作为统一事务边界。

## Migration Scope

1. 增加 function-scope `SessionDep`、共享 `get_write_db()`/`WriteSessionDep` 及其单元测试。
2. 枚举并迁移 API 路由中的 `POST`、`PUT`、`PATCH`、`DELETE`：用户、登录、items、private、IAM、inventory、scheduler。
3. 移除仅由 HTTP 调用的服务/CRUD 的 commit/rollback；对仍被 worker、CLI、导入或启动调用的函数，先改为由外部调用者显式提交。
4. 检查任务投递：HTTP 不直接 `.delay()`；需要异步执行的 scheduler run 保持持久化 `QUEUED`，由 scanner 在提交后投递。

## Failure And Rollback

- 业务、验证或完整性异常穿透依赖，Unit of Work 回滚所有本请求新增/更新状态。
- 认证、权限或 endpoint 在写依赖 yield 后失败时，function-scope teardown 在响应发送前回滚；依赖创建失败时不尝试提交；关闭 Session 仍由 `get_db()` 管理。
- 不在数据库事务内调用 SMTP、外部 HTTP 或 broker；外部操作留给异步边界。
- 无 schema 变化；回滚为恢复单个已迁移 HTTP 模块的原依赖和服务提交调用，不影响非 HTTP 事务。
