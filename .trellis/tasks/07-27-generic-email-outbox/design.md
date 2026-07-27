# Technical Design

## Persistence Model

`EmailOutbox` 是平台表，拥有 `BIGINT GENERATED ALWAYS AS IDENTITY` 和 `AuditFields`。每行只对应一个 recipient。固定 kind 使用受限枚举：

- `RENDERED`：recipient、subject 和 HTML snapshot。
- `ACCOUNT_SET_PASSWORD`：recipient、User reference；worker 在发送时生成 set-password link。
- `PASSWORD_RECOVERY`：recipient、User reference；worker 在发送时生成 recovery link。

状态至少区分 pending/leased/retry-wait/delivered/failed。行保存 attempt count、next attempt、lease expiry、delivered time 与有限安全 error category；不存在任意 class path、template payload JSON、明文密码或 JWT 字段。

## Producer Flow

HTTP 业务与 outbox 行在 P0 的同一 Unit of Work 写入。创建受管理 active 用户时写入 set-password row；恢复密码时只对 active 非 System Actor User 写 recovery row；测试邮件写 rendered row 并返回 202。scheduler 在锁住 Job 后，同时更新一小时 throttle 与为每个 recipient 插入 rendered row。没有 recipient 时不建行，但保持现有 throttle/log 行为。

HTTP 不调用 SMTP，也不发送 Celery message。Beat 的每分钟 scanner 从已经提交的 due rows 领取并发布 ID，最多引入一分钟发送延迟，从而消除 commit/enqueue race。

## Worker Flow

worker 接收单个 outbox ID，在短事务内以锁/lease 领取可投递行。随后离开事务并调用 `send_email()`；最后以独立事务写 delivered 或 retry state。重试每 15 分钟，总尝试最多 8 次。visibility timeout 是 worker lease 时间。SMTP 接受后进程丢失时允许 redelivery；数据库进度应保持可恢复。

链接邮件发送前重读 User：必须 active、非 System Actor、email 等于 queued recipient；否则记录 `RECIPIENT_INVALID` 终态。任何 retry、lease recovery、no-auth producer 使用 System Actor；有持久化人类发起者的首次投递保留该 actor。

## Boundaries And Rollback

库存日报保留独立 `InventoryDailyReportDelivery`，不迁移 snapshot 或 retry 语义。现有 HTML 模板和 `send_email()` SMTP transport 可复用，`generate_new_account_email()` 的明文密码路径必须删除/停止调用。

新增迁移可在隔离库往返；应用回退前必须停止 outbox scanner/worker 或保持旧版本可忽略 pending rows。无 retention 需求时不添加 purge。无 schema downgrade 能恢复已经发送的邮件。
