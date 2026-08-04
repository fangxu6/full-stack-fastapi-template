# 分阶段缓存机制 Deferred Iterations

## Purpose

本任务的当前交付是默认不启用业务缓存的通用基础能力。权限缓存、业务读取
缓存和报表快照各有独立的安全或数据新鲜度范围，因而只在此记录未来边界，
不作为本期验收或实现。

## Traceability Rules

- 延期项不构成本任务的实现或验收失败条件。
- 每个延期项开始实现前必须创建独立 Trellis 任务，完成自己的 PRD、设计、
  实现计划和比例合适的 API/E2E 验证。
- PostgreSQL 继续是权限事实来源；浏览器或 Redis 均不能成为授权来源。

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Redis 有效权限读模型缓存 `cache:v1:iam:effective:{user_id}`，只服务 `GET /iam/me/permissions` | 当前没有热点测量证据；缓存服务端授权会扩大撤权一致性风险 | 权限热点基线；本任务基础能力的连接/监控结论；提交后失效边界；按角色列出已分配用户 ID 的仓储查询 | 独立 PRD、设计、实现、API/E2E 测试与回滚方案 |
| D-002 | 将经测量的读多写少业务 GET 接入 Redis Cache-Aside | 当前没有已确认的慢查询；预设 TTL 会制造无收益的陈旧数据窗口 | 本任务基础能力；缓存前 P95/调用量基线；接口新鲜度预算；写入路径的精确失效清单 | 独立 PRD、性能证据、设计、实现、回归与故障回源测试 |
| D-003 | 对经确认的报表或复杂聚合采用 PostgreSQL 物化视图或可重建汇总快照 | 当前没有可复现的报表性能问题 | 查询计划/负载证据；刷新频率和数据新鲜度产品要求；迁移与回滚方案 | 独立 PRD、数据迁移、刷新任务、性能与一致性验证 |

## Carry-Forward Acceptance Notes

- key 必须有短 TTL，Redis 故障时回源 PostgreSQL；`permission_required()` 继续
  直接计算权限，不能读取该缓存作授权决定。
- 用户角色替换提交成功后，只失效该用户的有效权限 key。
- 角色权限替换或角色启停提交成功后，查询该角色的已分配用户并逐个失效其 key。
- 角色名称或描述修改不失效有效权限 key。
- 禁止全局前缀删除或“刷新全部权限缓存”接口。

## Suggested Iteration Order

1. D-002 或 D-001：仅在各自性能证据出现后独立启动；二者没有互相依赖。
2. D-003：仅在报表/聚合查询成为瓶颈后评估。

## Remaining Work In Current Scope

- 完成本任务的可选缓存基础能力与其事务、故障回源和指标验证。
