# 分阶段缓存机制设计

## Scope

本期只交付一个默认不缓存业务响应的 opt-in 基础能力。它不会改变任何 HTTP
响应、OpenAPI schema、前端 query 行为或数据库模型。具体业务 Cache-Aside、
权限读模型缓存和报表快照均保持在 [deferred-iterations.md](deferred-iterations.md)。

## Decisions

### Frontend

TanStack Query 继续使用现有 singleton `QueryClient` 和 query key。相同 key 的
并发读取由库去重；全局不设置 `staleTime`，所以动态读取仍默认立即过期。未来
业务接口只有在拥有新鲜度预算时，才在自己的 query options 中设置 `staleTime`
并在对应 mutation 成功后精确失效。

本期不新增前端代码、持久化浏览器缓存或 query-key 工厂。

### Redis Cache Primitive

在 `backend/app/core/cache.py` 放置一个同步 JSON 缓存实现，因为现有 FastAPI
路由和 SQLModel session 都是同步调用。`backend/pyproject.toml` 直接声明
`redis>=6.4,<7`，而不是依赖 `celery[redis]` 的传递依赖；当前 lock 已解析
`redis 6.4.0`。

`Settings` 通过现有 host/port/password 逻辑构造 `redis_cache_url`，固定使用
Redis database `2`。连接使用短、可配置的 connect/socket timeout；它们是运行
校准项，缓存故障不能无限阻塞 HTTP 请求。Celery broker/result 继续使用 database
`0`/`1`，不修改其配置或语义。

缓存模块只暴露下列显式原语：

```text
make_cache_key(namespace, identity) -> "cache:v1:<namespace>:<identity>"
get_json(key) -> JSON value | None
set_json(key, value, ttl_seconds) -> None
delete(*keys) -> None
record_cache_reload(elapsed_ms) -> None
defer_cache_invalidation(session, *keys) -> None
```

- `set_json` 必须收到正整数 TTL；没有默认 TTL，也不接受无限期缓存。
- 调用方必须提供 JSON 原生值；未来 Pydantic 响应使用 `model_dump(mode="json")`。
  缓存模块不序列化 ORM 实体，也不接受 loader callback。
- Redis 网络错误、编码错误和损坏 JSON 都视为 cache miss 或 no-op，并记录安全
  遥测。损坏 JSON 可 best-effort 删除后回源。
- 未来 Cache-Aside 调用方在回源完成后显式调用
  `record_cache_reload(elapsed_ms)`；该函数只记录回源耗时，不接受 loader callback
  或业务数据。
- 不提供 route middleware、自动装饰器、预热、批量前缀删除、锁或通用
  `get_or_set`。未来业务 Cache-Aside 仍在业务服务中显式表达读取、回源和写入。

### Transaction-Safe Invalidation

缓存失效键暂存在 `Session.info` 的专有 set 中。`get_write_db()` 的顺序为：

```text
route/service registers exact keys
        -> session.commit()
        -> delete registered keys best-effort
        -> session closes
```

如果 route、service 或 commit 抛出异常，依赖会 rollback 并丢弃登记的 key，绝不
删除缓存。提交后的删除失败仅发出错误遥测；数据库结果仍成功，有限 TTL 限制残留
陈旧窗口。

本期这个登记机制只属于 HTTP `WriteSessionDep`。Celery、CLI 和其他直接事务
owner 不自动参与；未来某个缓存业务由这些 owner 写入时，其独立任务必须明确
定义提交后失效边界。

### Observability

不新增 Prometheus 或第二套指标系统。扩展既有 `app.core.observability.log_event()`
的 allowlist，记录缓存操作类型、结果和耗时，并沿用 request-id 成功采样；Redis
错误不采样。日志不得包含 cache key、缓存值、用户 ID、查询条件、异常原文或
Redis URL。

日志可用于计算缓存 hit/miss 比、缓存操作 P95、回源/Redis 错误；既有
`http.request.*` 事件仍是 HTTP 请求 P95 的来源。没有业务调用方时缓存遥测为零
是预期结果，不应为此构造演示缓存。

## Compatibility And Rollback

- 没有 HTTP schema、路由或前端生成客户端变化；不运行 client generation。
- Redis 不在启动时强制 ping。缓存 client 延迟创建，未有调用方的环境与当前
  行为一致。
- 回滚代码只移除缓存模块、提交后 drain 和直接依赖；database `2` 的残留 key
  均有 TTL，不执行危险的 Redis `FLUSHDB`。
- 若直接依赖解析失败，停止在依赖安装阶段，不回退为依赖 Celery 的私有传递版本。

## Deferred Work

- D-001：只服务 `/iam/me/permissions` 的有效权限读模型缓存，保留精确失效规则，
  但不参与 `permission_required()`。
- D-002：经测量确认的业务 GET Cache-Aside 接入，届时定义 key 输入、新鲜度和
  写路径失效。
- D-003：经查询计划和负载证实需要的 PostgreSQL 物化视图或汇总快照。
