# 分阶段引入缓存机制

## Goal

在不改变 PostgreSQL 作为业务事实来源、后端逐请求授权判定或现有
Celery 语义的前提下，建立默认不缓存业务响应的可选缓存基础能力。它统一
客户端、键空间、TTL、提交后失效、故障回源和指标；具体业务接口只在出现
经测量的慢查询后才显式接入。

## Confirmed Facts

- 前端已经使用 TanStack Query；它会按 query key 复用同页并发请求。权限
  组件查询的 `staleTime` 为 30 秒，路由守卫会以 `staleTime: 0` 强制读取
  最新权限。
- 后端当前没有业务 Redis 缓存客户端。Redis 数据库 `0` 是 Celery broker，
  数据库 `1` 是短期 task result；PostgreSQL 仍是业务数据事实来源。
- 受保护接口通过 `permission_required()` 在服务端计算有效权限。权限结果
  缓存不能替代服务端授权。本期不实现 Redis 权限缓存；其受约束的未来候选
  已记录在 [deferred-iterations.md](deferred-iterations.md)。
- HTTP 写请求由 `WriteSessionDep` 在路由成功后统一提交。任何 Redis 失效
  都必须在提交成功后执行；Redis 故障不得阻断数据库读取或写入。

## Requirements

1. 保持 TanStack Query 为前端服务器状态缓存。全局 `staleTime` 维持安全的
   默认值，不把任何动态业务读取自动变为可陈旧；未来接口按自身新鲜度预算
   显式设置缓存策略和 mutation 后的精确失效。
2. 提供一个应用自有、按调用显式启用的 Redis JSON 缓存原语：带 TTL 的读取/
   写入、精确删除、稳定的 `cache:v1:` key 构造和缓存不可用时的非阻断回源。
   不提供路由中间件、全局自动缓存或无参数装饰器。
3. Redis 业务缓存与 Celery 分开使用数据库 `2` 和 `cache:v1:` 键前缀。直接
   使用 Redis 的代码必须声明直接依赖，不能依赖 `celery[redis]` 的传递安装。
4. 提供请求事务的提交后精确失效登记机制。它只能登记明确的 key，数据库
   回滚时不得删除，Redis 删除失败必须记录且由 TTL 限定陈旧窗口。
5. 记录命中、未命中、回源耗时和 Redis 错误；指标不包含 key 内容、用户标识
   或缓存值。未接入业务接口时指标为零是预期状态。
6. 保留权限读模型缓存、业务 Cache-Aside 接入和报表物化视图的延期边界，见
   [deferred-iterations.md](deferred-iterations.md)。

## Acceptance Criteria

- [x] 应用能以直接声明的 Redis 依赖连接数据库 `2`，并只使用 `cache:v1:`
      前缀；现有 Celery broker/result 的数据库 `0/1` 行为不变。
- [x] 缓存原语要求调用方提供有限 TTL，支持 JSON 值的读取、写入和精确删除；
      不含业务 endpoint、业务模型、全局中间件或自动缓存装饰器。
- [x] 写事务只有在提交成功后才执行已登记的精确失效；回滚不触发失效，Redis
      故障不阻断数据库成功响应或提交。
- [x] 指标可区分命中、未命中、回源耗时和 Redis 错误，且不记录缓存 key 或值。
- [x] 前端继续使用 TanStack Query 原生的 query key 去重；未为动态查询设置全局
      陈旧时间，也未新增 localStorage 权限快照。
- [x] 权限角色变更、用户角色变更和服务端 `permission_required()` 的授权语义
      不因缓存而放宽；延期项不构成本期实现验收。

## Out of Scope

- 本期将任何业务 GET 接口、权限读模型或报表查询接入 Redis 缓存，或为它们
  预设 TTL。
- 客户端持久化权限快照、分布式锁、缓存预热、全局缓存刷新 API、路由中间件、
  缓存框架或通用自动装饰器。
- 将 Celery broker、task result、锁、去重、限流或业务状态视为可随意删除的
  普通缓存。
- 未经性能证据的物化视图、汇总表或业务缓存 TTL。

## Technical Notes

- 这是跨 FastAPI、Redis、数据库事务与运行指标的复杂任务。技术设计、实施顺序
  和测试专用 API 生命周期验证分别见 [design.md](design.md)、
  [implement.md](implement.md) 和 [e2e-api-tests.md](e2e-api-tests.md)。
- 本期没有 HTTP schema 或前端生成客户端变化。
