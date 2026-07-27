# Python 横切能力改造

## Goal

把 HTTP 写请求、自动化写入、邮件投递和 Celery 任务日志统一到可验证的横切边界，减少服务层自行控制事务和异步副作用造成的不一致。

## Current State

- AI 库存查询及 sidecar 已在 `5f17e10` 中删除，本任务不再重复实施。
- 调度运行的投递租约、配置校验和每日库存日报已存在，日报仍保持领域专用投递记录。
- `AuditFields` 已用于新业务表，但 HTTP actor 传播和 System Actor 约束尚未完成。
- HTTP 路由、CRUD 和服务中仍存在直接 `session.commit()`；SMTP 测试邮件、欢迎邮件和密码恢复邮件仍未统一进入持久化发件箱。
- Celery 已使用 PostgreSQL 记录业务状态，但任务观测上下文需要收敛为安全的任务标识。

## Requirements

1. HTTP 写请求使用请求级 Unit of Work：成功后统一提交，异常统一回滚；服务、CRUD 和路由不得自行提交或回滚。读取请求继续使用现有只读会话依赖。
2. 所有可审计写入必须显式接收人类 User 或唯一的受保护 System Actor；禁止使用空值、哨兵 UUID、当前登录用户全局状态或伪造用户。
3. 调度、worker、CLI、迁移和补偿流程显式传递 actor；Celery 任务只传递业务 ID 和受控的 actor UUID，不传 ORM 对象、请求对象或敏感上下文。
4. 欢迎邮件、密码恢复邮件、测试邮件和调度告警邮件进入通用 `email_outbox`；库存日报继续使用现有领域专用投递表。
5. 发件箱必须保存收件人和渲染结果快照，按单收件人记录状态、尝试次数和安全失败类别；worker 负责领取、SMTP 投递和结果落库，保持至少一次语义。
6. Celery 使用生命周期 signal 记录任务开始、成功和失败事件，仅允许记录 broker task id、任务名和安全结果类别；不得记录参数、token、邮件正文、actor UUID 或 ORM 数据。
7. 迁移、API、任务和文档测试覆盖事务回滚、actor 约束、发件箱幂等/重试和安全日志边界。

## Child Task Order

按以下顺序实施。父任务不直接修改业务代码，只维护跨子任务范围、依赖和最终集成验收。

1. `07-27-request-unit-of-work`（P0，基础且关键）：建立 HTTP 写请求事务边界；后续邮件入队依赖其原子提交语义。
2. `07-27-explicit-audit-actor`（P1，基础）：建立显式 actor 与 System Actor；后续无认证 worker/补偿写入依赖它。
3. `07-27-safe-celery-observability`（P2，剩余）：统一安全任务生命周期日志；不依赖业务 outbox，先落地以便后续异步投递可观察。
4. `07-27-generic-email-outbox`（P2，剩余）：建立持久化邮件投递；依赖 1 的事务边界与 2 的 actor 语义，并使用 3 的安全任务观测。

## Acceptance Criteria

- [ ] HTTP `POST/PUT/PATCH/DELETE` 写路径在 endpoint 成功后提交，在 endpoint 或服务异常后回滚；服务层不再调用 `commit()`/`rollback()`。
- [ ] HTTP 写入和异步写入均能验证 actor；System Actor 只能由受控内部流程使用，不能通过普通用户管理接口操作。
- [ ] 欢迎、恢复、测试和调度告警邮件先形成持久化 outbox 记录，再由 Celery worker 投递；SMTP 失败可安全重试，已成功收件人不重复发送。
- [ ] 任务日志不包含任务参数、密钥、token、邮件内容或用户标识，仅包含允许的任务标识和失败类别。
- [ ] Alembic 升级/降级、现有登录/用户/调度/库存 API 以及 Celery eager 测试通过；生成的 OpenAPI 客户端如有变化按仓库流程同步。
- [ ] 四个子任务按上述顺序完成各自验收；父任务完成跨模块回归、迁移往返和最终集成审查。
- [ ] 任务仍为 `planning`，未执行 `task.py start`；实现前须由用户审核并确认计划。

## Out Of Scope

- 不重新实现已删除的 AI 库存查询或 sidecar。
- 不改造库存日报为通用 outbox，不新增告警平台、站内通知、排班、确认或升级链路。
- 不引入新的任务队列、APScheduler、消息总线或第二套事务抽象。
- 不提供 outbox 管理 API/UI；首期通过数据库记录、Celery 日志和 SMTP 失败日志追踪。

## References

- `docs/adr/0003-item-service-owns-transactions.md`（已废止）
- `docs/adr/0006-use-request-scoped-unit-of-work-for-http-writes.md`
- `docs/adr/0007-require-an-explicit-audit-actor.md`
- `docs/adr/0009-use-generic-email-outbox-for-non-report-mail.md`
- `docs/adr/0010-use-safe-celery-task-observability-context.md`
