# API E2E Validation Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: 使用独立测试 PostgreSQL 数据库。

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | AuditFields 资源创建/更新 | 认证人类 User | 合法库存或 scheduler 写请求 | 现有成功响应 | created/updated actor 都等于认证 User；更新时间为 UTC | 服务层不接受客户端 audit 字段 |
| E2E-002 | System Actor 用户管理保护 | 已初始化 System Actor 与管理员 | 列表、详情、更新、删除、角色分配请求 | 列表不出现；直接操作为现有拒绝/未找到语义 | System Actor 与角色保持不变 | 不暴露其 UUID、email 或密码 |
| E2E-003 | 无 actor 审计写入 | 测试依赖或内部调用缺 actor | 触发 AuditFields 持久化 | 失败且保持统一错误边界 | 无业务行或审计行提交 | 不回退为 NULL/哨兵 UUID |

## Execution

- 使用新 Session 检查 actor 字段，不依赖 ORM 内存对象。
- 异步 actor 传播由 scheduler/worker 单元及集成测试补充验证。
