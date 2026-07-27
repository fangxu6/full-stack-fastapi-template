# Technical Design

## Actor Source

审计来源仅为当前 SQLAlchemy `Session.info["actor_id"]`。HTTP 的 `WriteSessionDep` 在认证后绑定人类 User UUID；worker、CLI、bootstrap 和补偿入口创建 Session 后先显式绑定 UUID。日志 contextvars、请求对象、全局变量和 ORM detached User 均不是 actor 来源。

在 flush 前的 ORM hook 检查每个新增或修改的 `AuditFields` 实体：无 actor 直接失败。新增实体获得同一 UTC 时间及 creator/updater；已持久化实体只更新 updater，并拒绝 creator/created time 改变。`deleted_at` 是业务字段，软删除和恢复可改变它但仍更新 updater。

## System Actor

User 模型增加私有 `is_system_actor`。迁移创建 PostgreSQL partial unique index，约束 `is_system_actor = true` 最多一行；初始化幂等查询或创建该行。其 email 仅为 display address，密码随机且不可使用，不授予角色、不允许登录。用户查询、详情、更新、删除与角色分配统一排除/拒绝 System Actor。

## Migration Scope

1. 迁移 User 标记、partial unique index 与必要的受保护数据初始化路径。
2. 实现 actor bind helper 与 ORM hook；为既有 AuditFields 模型统一接入。
3. P0 完成后，在 HTTP 写依赖中绑定认证 actor，删除服务层的 audit field 赋值。
4. 更新 scheduler/worker/CLI/bootstrap 调用点：手工 run 传递 `requested_by`，无认证自动运行和 retry 解析 System Actor。

## Failure And Rollback

- 任何缺失 actor 或 creator 篡改使当前事务失败并回滚，不能写入半审计记录。
- System Actor 标记/约束迁移可 downgrade；不会删除历史业务数据。
- 回退时先停止依赖该 hook 的新 writer，避免旧应用在新约束下以无 actor 写入。
