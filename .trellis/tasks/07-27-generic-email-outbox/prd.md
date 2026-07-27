# 通用邮件发件箱

## Goal

将欢迎、密码恢复、测试邮件和 scheduler 告警从同步 SMTP 调用迁移为可追踪的持久化单收件人 outbox。HTTP 只承诺写入投递请求，Celery 在提交后的异步边界发送邮件并记录结果。

## Confirmed Facts

- `services/user.py`、`services/auth.py`、`api/routes/utils.py`、`core/tasks.py` 和 `modules/scheduler/tasks.py` 当前直接调用 `send_email()`。
- 库存日报已有 `inventory_daily_report` 和 `inventory_daily_report_delivery`，包含冻结快照、逐邮箱重试和日报领域状态；它不适合改造成通用 outbox。
- Celery 已使用默认单队列、JSON 参数、late ACK 与 visibility timeout；Worker 可只接收数值 ID 并打开自己的数据库 Session。
- scheduler 告警已经有 one-hour throttle 和配置收件人，但目前在 task 内同步发送邮件。
- P0 会提供 HTTP 原子提交；P1 会提供 System Actor 和异步 actor 传播；P2 会提供安全任务生命周期日志。

## Requirements

1. 新建审计化 `email_outbox`，使用 BIGINT identity，每个收件人一行，记录 kind、recipient、状态、尝试次数、下次尝试、租约、终态时间与安全失败类别。
2. 固定 kind：`RENDERED` 保存 recipient/subject/html 冻结快照；`ACCOUNT_SET_PASSWORD` 与 `PASSWORD_RECOVERY` 只保存 recipient 和 User 引用，不保存明文初始密码或密码恢复 JWT。
3. 新账号仅在受管理用户创建且 active 时创建 set-password outbox；禁用用户创建或之后启用都不自动邀请。链接由 worker 发送时生成，因此 retry 可以得到新 token。
4. 密码恢复只为 active、非 System Actor User 创建 outbox；未知、禁用和 System Actor 的恢复请求返回相同枚举安全响应且不建投递记录。
5. worker 只接收 outbox ID：事务内领取一条可投递行，事务外执行 SMTP，再以新事务记录结果。每行共 8 次、每 15 分钟重试、visibility timeout 作为租约；SMTP 接受后崩溃允许重复发送但不能静默漏发。
6. 每次链接类投递前重新检查用户 active、非 System Actor 且 email 匹配；不匹配标记终态 `RECIPIENT_INVALID`，不发送不重试。
7. scheduler alert 在锁定 Job、应用 throttle 和更新 throttle 时间的同一事务中为每个配置收件人插入 `RENDERED` outbox；无收件人时不插入，但仍推进 throttle 并每小时记录一次 `scheduler.alert.unsent`。
8. Beat 每分钟扫描 due outbox；HTTP 不直接 `.delay()`。每日 09:00 测试邮件改为创建 System Actor 的 rendered outbox；测试邮件 API 返回 `202` 和 `Test email queued`。
9. SMTP 缺失不阻止合法 outbox 记录创建；worker 将其记为 `SMTP_NOT_CONFIGURED` 并按正常策略重试。首期不提供管理 API/UI、清理或内容 purge。

## Acceptance Criteria

- [ ] 迁移创建带命名约束、审计字段、BIGINT identity 与一收件人一行约束的 `email_outbox`。
- [ ] 四类生产者均先持久化 outbox，再由 worker 投递；HTTP 路径不再同步 SMTP 或直接发布 task。
- [ ] worker 正确处理成功、SMTP 失败、配置缺失、租约恢复、8 次终止、已成功不重发与链接 recipient invalid。
- [ ] 欢迎和恢复邮件不保存明文密码/JWT；恢复接口保留枚举安全；测试邮件 API 返回 `202`。
- [ ] scheduler throttle 与 alert outbox 行同一事务；库存日报继续使用自己的 delivery 表且不复用 `email_outbox`。
- [ ] 所有 outbox 业务状态可从数据库追踪，日志仅含 P2 允许的任务字段和 SMTP dependency 事件。

## Out Of Scope

- 不迁移或删除库存日报的 `InventoryDailyReportDelivery`。
- 不增加邮件管理 API、前端页面、站内通知、告警平台、批量邮件或内容保留清理任务。
- 不保证 exactly-once SMTP；接受 worker 故障时的可见重复邮件。
- 不新增 Celery 队列、task route、全局 retry 或同步 fallback 发送。

## Dependencies

- 前置：`07-27-request-unit-of-work`、`07-27-explicit-audit-actor`、`07-27-safe-celery-observability` 必须完成并提交。
- 决策依据：`docs/adr/0009-use-generic-email-outbox-for-non-report-mail.md`。
