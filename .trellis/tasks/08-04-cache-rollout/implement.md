# 分阶段缓存机制实施计划

## Ordered Checklist

1. 在 `backend/pyproject.toml` 显式加入锁文件当前使用的 `redis>=6.4,<7`，更新
   `uv.lock`，并扩展 `Settings` 的 cache database `2` URL 与短 timeout 设置。
2. 新建 `backend/app/core/cache.py`：同步、延迟创建的 Redis client；JSON
   `get_json`、`set_json`、`delete`、key 构造、回源耗时记录和提交后失效登记。
   所有外部 Redis 错误在模块边界吞掉并转换为安全遥测。
3. 修改 `backend/app/api/dependencies/database.py`：只有 `session.commit()` 成功后
   drain 已登记 key；异常路径 rollback 并清理登记，不触发 delete。
4. 扩展 `backend/app/core/observability.py` 的事件和字段 allowlist，记录无敏感
   数据的缓存操作结果与耗时；更新其保护性测试。
5. 添加配置、缓存原语和请求 Unit of Work 的聚焦测试。不接入任何业务 endpoint、
   ORM model、前端 query 或权限授权路径。
6. 执行聚焦测试、完整 backend lint gate、空白差异检查。确认 OpenAPI 无变化，
   不运行生成客户端脚本。

## Planned Files

| File | Change |
| --- | --- |
| `backend/pyproject.toml` | 直接声明 `redis` runtime dependency |
| `uv.lock` | 记录直接依赖关系 |
| `backend/app/core/config.py` | database `2` cache URL 和超时配置 |
| `backend/app/core/cache.py` | 新的最小 opt-in JSON cache primitive |
| `backend/app/api/dependencies/database.py` | 成功提交后的精确失效 drain |
| `backend/app/core/observability.py` | 缓存安全遥测 allowlist |
| `backend/tests/core/test_config.py` | cache URL、密码和 timeout 验证 |
| `backend/tests/core/test_cache.py` | JSON、TTL、错误回源和 key 约束 |
| `backend/tests/api/test_request_unit_of_work.py` | commit/delete/close 与 rollback/no-delete 顺序 |
| `backend/tests/core/test_observability.py` | 缓存遥测的字段红线 |
| `.trellis/spec/backend/cache-guidelines.md` | 可选 Redis 缓存、提交后失效与遥测契约 |
| `.trellis/spec/backend/index.md` | 链接缓存 code-spec 和触发条件 |

## Validation

```powershell
$env:POSTGRES_DB = 'aiadmin_test'
bash -lc 'cd backend && uv run pytest tests/core/test_config.py tests/core/test_cache.py tests/core/test_observability.py tests/api/test_request_unit_of_work.py'
bash -lc 'cd backend && ./scripts/lint.sh'
git diff --check
```

测试使用现有 isolated `aiadmin_test` 合同。缓存原语使用 test double 模拟 Redis
成功、超时和损坏 JSON；不得把开发数据库或生产 Redis 清理作为验证手段。

## Review Gates

- `get_write_db()` 的成功、commit 失败和 route 异常路径都确认只在成功提交后删除。
- 日志测试断言 key、值、用户标识、URL 和异常文本无法传入 allowlist。
- Redis client 失败时 `get_json` 返回 miss，写/删不抛出，业务调用方将来可回源。
- 没有业务 endpoint 或 `permission_required()` 导入/调用 cache primitive。
- 没有 API schema 变化；generated client 和 route tree 均不变。

## Rollback

删除本计划新增的 cache module、配置字段、数据库依赖 drain、遥测字段及其直接
依赖声明。不要执行 Redis `FLUSHDB`；缓存 key 由 TTL 自然过期。
