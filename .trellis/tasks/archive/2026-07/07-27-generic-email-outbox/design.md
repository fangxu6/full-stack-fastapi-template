# Technical Design

## Persistence Model

`EmailOutbox` 是平台表，拥有 `BIGINT GENERATED ALWAYS AS IDENTITY` 和 `AuditFields`。数据库对象使用 `email_` 前缀；每行只包含一个标量 `recipient`，没有收件人数组或群发模型。固定 kind 使用受限枚举：

- `RENDERED`：recipient、subject 和 HTML snapshot。
- `ACCOUNT_SET_PASSWORD`：recipient、User reference；worker 在发送时生成 set-password link。
- `PASSWORD_RECOVERY`：recipient、User reference；worker 在发送时生成 recovery link。

状态固定为 `PENDING`、`LEASED`、`RETRY_WAIT`、`DELIVERED`、`FAILED`。行保存 `attempt_count`（0--8）、`next_attempt_at`、`lease_expires_at`、`delivered_at`、`failed_at` 与有限的安全 `last_error_category`；`RENDERED` 要求 subject/HTML 且没有 User 引用，链接类要求 User 引用且没有 subject/HTML。数据库 check constraint 约束这两种形状、次数范围和允许的失败类别；部分 due index 仅覆盖 `PENDING`/`RETRY_WAIT`。

没有任意 class path、template payload JSON、明文密码或 JWT 字段。`ACCOUNT_SET_PASSWORD` 保留现有受管理用户创建 API 的密码哈希，以保持兼容，但 worker 使用 `/reset-password` JWT 重新渲染不含密码的 `new_account.html`；JWT 只在 worker 内存中存在。

## Producer Flow

HTTP 业务与 outbox 行在 P0 的同一 Unit of Work 写入。创建受管理 active 用户时写入 set-password row；public signup、disabled-user 创建和之后启用均不写邀请。恢复密码只对 active 非 System Actor User 写 recovery row；测试邮件写 rendered row 并返回 202。拥有 outbox 写入的认证 HTTP 路径使用已存在的 `AuditedWriteSessionDep`；无认证恢复绑定 System Actor 并让其存活至请求级提交。

scheduler 以 `FOR UPDATE` 锁住 Job，在同一事务中更新一小时 throttle 与为每个 recipient 插入 rendered row。没有 recipient 时不建行，但仍推进 throttle 并在事务后记录一次 `scheduler.alert.unsent`。SMTP 配置不参与生产者判定。

HTTP 不调用 SMTP，也不发送 Celery message。Beat 每分钟先在短事务中把过期 `LEASED` 行恢复为 `RETRY_WAIT`，再读取 due IDs 并提交；提交后才对每个 ID 调用 delivery task。broker 失败不修改业务状态，下一分钟会重新扫描。

## Worker Flow

worker 接收单个 outbox ID，在短事务内 `FOR UPDATE` 领取可投递行：已终态、尚未到期或仍有效租约的行直接跳过；超时租约先按 System Actor 恢复；第九次领取前终态失败。worker 离开事务后调用 `send_email()`，最后以独立事务、且仅在同一 lease 仍有效时写 delivered 或 retry state。重试每 15 分钟，总尝试最多 8 次。visibility timeout 是 worker lease 时间。SMTP 接受后进程丢失时允许 redelivery；数据库进度应保持可恢复。

链接邮件发送前重读 User：必须 active、非 System Actor、email 等于 queued recipient；否则由 System Actor 记录 `RECIPIENT_INVALID` 终态。首次人工投递的领取和结果保留创建者；System Actor 创建的行、重试、租约恢复和终态补偿使用 System Actor。所有邮件内容、recipient、actor UUID 与异常文本保持在数据库/内存边界之外，不进入日志。

## Boundaries And Rollback

库存日报保留独立 `InventoryDailyReportDelivery`，不迁移 snapshot 或 retry 语义。其三段 delivery 模式和现有 HTML 模板/`send_email()` SMTP transport 可复用；`generate_new_account_email()` 的明文密码输入和模板字段必须删除。

新增迁移可在隔离库往返；应用回退前必须停止 outbox scanner/worker 或保持旧版本可忽略 pending rows。无 retention 需求时不添加 purge。无 schema downgrade 能恢复已经发送的邮件。
