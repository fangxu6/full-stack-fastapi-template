# API E2E Validation Plan

## Scope

验证 HTTP 写请求的请求级事务和邮件入队边界；Celery worker、迁移和日志另由后端测试与隔离运行时验证。

## Cases

### Successful HTTP write

- Setup: 创建已认证普通用户和测试数据库会话。
- Request: 调用一个用户、IAM 或库存 `POST/PUT/PATCH/DELETE` 写接口。
- Expected: HTTP 成功响应；业务行和审计 actor 在同一事务提交；若触发邮件，存在对应 outbox 行。
- Side effects: 不直接执行 SMTP；Celery 只接收持久化记录 ID。

### HTTP write rollback

- Setup: 准备会在业务校验或持久化阶段失败的写请求。
- Request: 发送该请求并等待标准错误响应。
- Expected: 返回项目统一错误结构和 request id。
- Persistence: 业务行、审计更新和同事务 outbox 行均不存在或保持原值。

### Password recovery / test email enqueue

- Setup: 配置 SMTP 测试替身，准备 active non-System user。
- Request: 调用密码恢复或测试邮件接口。
- Expected: API 返回现有通用成功/已排队语义；数据库存在一条受控 recipient/subject/html 快照 outbox 行。
- Side effects: HTTP 请求不调用 SMTP；恢复请求不暴露用户是否存在或 token。

### Outbox delivery failure

- Setup: 使用 eager Celery 和失败 SMTP 替身，准备一条待投递 outbox 行。
- Request: 触发 outbox delivery task。
- Expected: 记录安全失败类别、尝试次数和下次重试时间；不写入异常正文、密码或 token。
- Retry: 重试达到上限后变为终态；成功收件人不会再次发送。
