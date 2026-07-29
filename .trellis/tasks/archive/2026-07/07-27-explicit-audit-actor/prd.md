# 显式审计 Actor 与 System Actor

## Goal

让每一次 `AuditFields` 持久化都有可验证的行为主体：认证 HTTP 请求使用其人类 User；无认证自动化写入使用受保护、可区分的 System Actor；异步的人类发起操作保留原始人类 actor。审计 actor 只存在于事务内的 `Session.info`，不进入运行日志或公共 API。

## Confirmed Facts

- `07-27-request-unit-of-work` 已提交。`WriteSessionDep` 复用认证/RBAC 的请求缓存 Session，并在成功响应前提交、异常时回滚；它目前尚未绑定 audit actor。
- 只有八张现有表继承 `AuditFields`：库存的 `ProcessingUnit`、`ReceivingUnit`、`InventoryDocument`、`InventoryDocumentLine`、`InventoryImportBatch`、`LegacyImportRow`、`InventoryLedgerEntry`，以及 `SchedulerJob`。`User`、`Item`、`SchedulerRun`、日报和投递表不在本次 hook 覆盖范围内。
- `AuditFields` 的 UTC 创建/更新字段由 `Session.before_flush` hook 统一维护；八张继承表不再由库存、导入或 scheduler service 手工赋值。
- `User` 具有私有的 `is_system_actor` 与 `system_actor_key`，后继迁移以 check constraint 和 key 的 partial unique index 支持多个受保护 System Actor；认证、恢复、用户管理和 IAM 角色分配均排除它们。
- `init_db()` 在管理员与 scheduler bootstrap 前幂等预置默认 key `system`，并在同一 Session 中绑定它完成自动化 `SchedulerJob` 写入。
- `SchedulerRun.requested_by` 保持手工/定时的业务归因，`ScheduledTaskContext` 携带持久化 actor UUID；worker 的执行、扫描和告警路径在各自独立 Session 中显式绑定 actor。
- CLI 库存导入接收 `actor_user_id`，接受活跃人类或已预置的 System Actor，拒绝缺失用户与停用的人类用户，并保留自身显式 commit/rollback 所有权。
- 现行日志契约只允许 `actor_kind`，禁止 actor UUID、email、角色、token 或任务参数出现在 HTTP/Celery structlog context。

## Requirements

1. 为 `User` 增加私有 `is_system_actor: bool` 与 `system_actor_key: str | None`。System Actor 必须有非空 key，普通 User 必须没有 key；数据库以 check constraint 维持该关系，并以 `system_actor_key` 的 partial unique index 保证每个 key 至多一个受保护账号。默认 key `system` 仍由启动初始化创建为 `system@example.com`、随机不可用密码、`is_active=false`、无角色的行；其他 key 只可由受控 provisioning command 以显式 key 和 display email 幂等预置。标记与 key 而非 email 是运行时身份。
2. 建立明确的 `bind_audit_actor(session, actor_id)` / `require_system_actor(session)` 边界。bind helper 只在当前 Session 存入已验证、仍存在的 UUID；允许非活跃 System Actor，不能使用 detached `User`、contextvars、请求对象或全局当前用户。
3. 建立 `before_flush` ORM hook，仅检查 `session.new` 与实际修改的 `session.dirty` 中的 `AuditFields` 实体。插入时由 hook 覆盖四个创建/更新字段为同一 UTC 时刻和 actor；更新时只设置 updater 字段，并拒绝持久化 `created_at` 或 `created_by` 的改变。缺 actor、非法 actor 或 creator 篡改使整个事务失败；`deleted_at` 的软删除/恢复仍是普通业务变更并更新 updater。
4. HTTP 中所有可能写入 `AuditFields` 的库存和 scheduler 路由在同一个 `WriteSessionDep` 上绑定 `CurrentUser.id`。移除库存与 scheduler service 的手工 AuditFields 赋值，但保留 `SchedulerRun.requested_by` 这一业务归因字段。`User`、注册、登录和密码恢复等不继承 `AuditFields` 的写入不因此获得伪造的 System Actor。
5. 每个非 HTTP 的审计写入口在首次审计写入前绑定 actor：库存 CLI 可使用调用方提供的活跃人类 `actor_user_id`，或已预置受保护 System Actor 的 UUID；它拒绝不存在的用户和停用的普通用户。scheduler 的定时扫描、无人工来源的 run、告警和 bootstrap 使用默认 key `system`；手工 run、backfill、重试和其后对 `AuditFields` 的写入继续使用持久化的 `requested_by`。`ScheduledTaskContext` 只传 actor UUID，不传 detached `User`；不写入 `AuditFields` 的日报和投递 Session 保持现有技术记录行为。
6. System Actor 不能认证或获得 token，即使错误配置为 active；密码恢复、重置、HTML 预览和当前 token 也必须拒绝它。用户列表排除它，按 ID 读取返回不暴露其存在的语义，任何更新、删除或角色替换在 service 层拒绝。公开 schema 不声明该标记。
7. 不在 hook 范围内的模型保持现有时间戳行为。不得为此追溯迁移 `User`、`Item`、`SchedulerRun`、日报或投递表，也不得以日志上下文替代数据库审计。

## Acceptance Criteria

- [x] 迁移为 `User.is_system_actor` / `system_actor_key` 创建非空关系约束与按 key 的 partial unique index；默认 `system` 初始化重复和并发执行最终仅保留一个账号，两个不同 key 可各自预置一个受保护账号，且不会因其自身创建触发 AuditFields 约束。
- [x] 八张现有 AuditFields 表的 insert/update 均由 hook 写入 actor 与 UTC 时间；insert 的 creator/updater 对相同，update 不改 creator，显式 creator 篡改和缺 actor 都会回滚整笔事务。
- [x] 已认证库存和 scheduler HTTP 写入使用同一请求 Session 中的当前用户，库存/scheduler service 与 importer 不再直接赋值 audit 字段。
- [x] scheduler 任务上下文保留手工 `requested_by`；定时、bootstrap、告警及无人工来源的 `SchedulerJob` 写入使用 key 为 `system` 的 System Actor。CLI import 接受活跃人类或已预置 System Actor，拒绝不存在和停用普通用户；日报和投递技术记录不被纳入 audit hook。
- [x] System Actor 无法登录、使用已有 token、进入密码恢复/重置流程、出现在用户列表或被用户/角色接口读取、修改、删除或分配角色；其标记不出现在公开 DTO。
- [x] 注册和其他不继承 AuditFields 的实体维持现有 API 与持久化行为；日志中没有 actor UUID、email、角色或 token。
- [x] 在隔离数据库 `aiadmin_test` 上验证迁移升级、默认/自定义系统账号预置的幂等性、key 唯一约束竞争路径和批准的回滚策略。

## Out Of Scope

- 不把 actor UUID、email、角色或权限写入 HTTP/Celery 日志上下文。
- 不引入跨租户 actor 模型、用户可配置的运行时凭据，或通过公开用户管理 API 创建 System Actor。
- 不将旧 `User`/模板 `Item` 追溯为完整 AuditFields；不把 `SchedulerRun`、日报或投递表纳入 hook。
- 不实现邮件 outbox 的投递状态；后续子任务消费本任务的 System Actor 和异步 actor 传播契约。

## Migration And Rollback Decision

- 已确认：System Actor 标记、key 唯一约束和 ORM 审计 hook 是 forward-only 契约。一旦任一 System Actor 被审计外键引用，普通 `alembic downgrade` 不得移除该机制或该 User 行；若已有多个 System Actor，也不得回退到仅允许一个的旧 boolean index。撤回通过前向修复或数据库备份恢复完成。
- 原因：删除该 User 会违反审计外键；仅删除标记会让旧应用将它当作普通用户暴露或修改。真实 PostgreSQL 验证已覆盖 fresh `a8b4c2d6e9f0 -> f2a8c7d1e6b4` 回退/重新升级，及有审计引用时的拒绝。

## Dependencies

- 前置：`07-27-request-unit-of-work` 已完成并提交（`9f69027`）。
- 后续：`07-27-generic-email-outbox` 依赖本任务的 System Actor 和异步 actor 传播。
- 决策依据：`docs/adr/0007-require-an-explicit-audit-actor.md` 与 `docs/adr/0006-use-request-scoped-unit-of-work-for-http-writes.md`。
