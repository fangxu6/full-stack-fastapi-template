# Technical Design: 主从数据库读写依赖预留

## Current Boundary

当前 `backend/app/core/db.py` 创建单个 `engine`。`get_db()` 在
`backend/app/api/dependencies/database.py` 创建 function-scope Session；
`WriteSessionDep` 复用这个 Session，并在请求结束时提交或回滚。认证模块的
`SessionDep` 继续依赖同一个 `get_db()`，因此认证、权限和写请求共享主库 Session。

## Configuration

在 `Settings` 中增加可选字段：

```text
POSTGRES_READ_REPLICA_SERVER: str | None = None
```

读库 URI 复用当前 `POSTGRES_PORT`、`POSTGRES_DB`、`POSTGRES_USER` 和
`POSTGRES_PASSWORD`，只覆盖 host。空值表示尚未配置读库。

## Engine Selection

`core/db.py` 保持现有 `engine` 导入兼容性：

```text
write_engine = create_engine(primary_uri)
read_engine = write_engine                         # 未配置读库
read_engine = create_engine(read_replica_uri)      # 已配置读库
engine = write_engine
```

未配置从库时必须复用同一 engine 对象，避免空配置产生第二个连接池。所有当前
直接导入 `engine` 的 prestart、Alembic、Celery、后台任务和测试继续连接主库。

## Dependency Contracts

新增 `get_read_db()` 和 `ReadSessionDep`，放在数据库依赖模块：

```text
get_read_db() -> Session(read_engine) -> yield -> close
ReadSessionDep = Annotated[Session, Depends(get_read_db, scope="function")]
```

`get_read_db()` 不依赖 `get_db()`，因此使用 `ReadSessionDep` 的 endpoint 会获得
独立的读库 Session。它不提交、不回滚，也不处理缓存失效。数据库级只读能力由
未来 PostgreSQL hot standby 和读账号保证，不在应用 Session 中实现自动 SQL
判断。

现有契约保持不变：

```text
SessionDep      -> get_db()       -> write_engine
WriteSessionDep -> get_write_db  -> get_db() -> write_engine
ReadSessionDep  -> get_read_db() -> read_engine
```

`ReadSessionDep` 从数据库依赖模块导出，并通过 `app.api.deps` 对路由提供；不把
`SessionDep` 从认证模块迁移，避免扩大现有导入和测试范围。

## Route Scope

首批只迁移查询本身不写入、且允许复制延迟的读接口：

- `modules/scheduler/router.py`: `read_jobs`, `read_job`, `read_runs`。
- `modules/inventory/router.py`: `export_inventory_ledger`,
  `read_processing_units`, `read_receiving_units`,
  `read_inventory_documents`, `read_inventory_document`,
  `read_raw_balances`, `read_finished_balances`, `read_inventory_ledger`,
  `read_inventory_suggestions`。

这些路由若同时使用 `CurrentUser` 或 `permission_required()`，认证和权限仍从
主库读取，业务查询使用读库 Session。

以下边界暂不迁移：

- `get_current_user()`、IAM 当前用户权限和权限校验依赖。
- 用户详情、当前用户详情、items 查询和库存纠正状态查询。
- 任何写后立即读取、读写混合或必须强一致的业务流程。

## Failure and Consistency

- 没有读库配置时，读请求继续使用主库，不产生行为变化。
- 有读库配置但连接失败时，错误直接暴露给现有数据库错误处理，不自动回退主库。
- 首批读接口接受异步复制延迟；写请求响应和认证结果始终来自主库。
- 读库健康检查、复制延迟告警、主从晋升和流复制配置属于后续基础设施 task。

## Compatibility and Rollback

- 不修改模型、迁移、OpenAPI schema 或前端生成文件。
- 回滚应用改动时，移除首批路由的 `ReadSessionDep` 使用即可；保留配置字段不影响主库运行。
- 若读库上线后发现一致性问题，暂时清空 `POSTGRES_READ_REPLICA_SERVER` 即可让读依赖复用主库。
