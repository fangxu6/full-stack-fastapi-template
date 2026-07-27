# 显式审计 Actor 与 System Actor

## Goal

让每一次 `AuditFields` 写入都有可验证的行为主体：HTTP 使用认证人类 User；无认证自动化流程使用唯一、受保护的 System Actor；异步的人类发起操作保留原始人类 actor。

## Confirmed Facts

- `AuditFields` 已定义 `created_at/created_by/updated_at/updated_by/deleted_at`，但当前调用方直接填充 actor 字段。
- `User` 目前没有 `is_system_actor` 标记或唯一性约束；普通用户接口和角色管理尚未排除系统用户。
- 当前认证依赖得到的 User 与 SQLAlchemy Session 共享请求缓存会话；P0 将把 HTTP 写事务统一为 `WriteSessionDep`。
- 库存导入已显式接受 `actor_user_id`；scheduler run 存在人类发起与自动运行两种来源；worker 会为每个任务创建独立 Session。

## Requirements

1. 为 `User` 增加私有 `is_system_actor` 标记和数据库 partial unique index，保证只有一个 System Actor；初始化幂等创建 `system@example.com`、随机不可用密码、无角色、不可登录的行。标记而非邮箱是身份。
2. 建立 ORM audit hook：只从 SQLAlchemy `Session.info` 读取 actor UUID；插入时设置四个创建/更新字段，更新时设置 updater 字段，拒绝修改持久化的 `created_at/created_by`。
3. HTTP 写依赖把认证 User UUID 绑定到当前 Session；业务服务和路由不再手工填写 AuditFields。
4. Worker、CLI、启动初始化和补偿流程在各自 Session 上显式绑定 actor。持久化的人类发起信息（例如 scheduler `requested_by`）应继续传播；无认证创建、重试、租约恢复和补偿使用 System Actor。
5. System Actor 不可登录、不可列出、不可直接读取、不可修改、不可删除、不可分配角色；它仅是审计归属目标。
6. 缺少 actor 的审计写入必须失败；不得回退到 `NULL`、哨兵 UUID、日志上下文、全局当前用户或伪造用户。

## Acceptance Criteria

- [ ] 独立迁移创建 System Actor 标记和 partial unique index；初始化多次运行只保留一个受保护 actor。
- [ ] 对 AuditFields insert/update 的创建者、更新者和 UTC 时间戳由 hook 统一维护；篡改 creator 字段的写入失败。
- [ ] 每个 HTTP AuditFields 写入从认证 User 得到 actor；服务层无手工 audit field 填写。
- [ ] scheduler、worker、CLI、bootstrap 与补偿路径显式提供人类 actor 或 System Actor；异步人类发起操作不丢失原 actor。
- [ ] System Actor 不能通过认证、用户管理或角色接口访问或变更。
- [ ] 注册等不继承 AuditFields 的实体保持原有行为。

## Out Of Scope

- 不把 actor UUID、email、角色或权限写入 HTTP/Celery 日志上下文。
- 不引入用户可配置的服务账号、多 System Actor 或跨租户 actor 模型。
- 不将旧 `User`/模板 `Item` 追溯为完整 AuditFields；仅覆盖当前继承 AuditFields 的表与本任务新增表。
- 不实现邮件 outbox 的投递状态；后续子任务消费该 actor 机制。

## Dependencies

- 前置：`07-27-request-unit-of-work` 必须完成并提交。
- 后续：`07-27-generic-email-outbox` 依赖此任务的 System Actor 和异步 actor 传播。
- 决策依据：`docs/adr/0007-require-an-explicit-audit-actor.md`。
