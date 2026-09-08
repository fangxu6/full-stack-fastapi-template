# Hanqiang 能力 prod 文档

这些文档把 `docs/hanqiang-core-contributions/` 的提交证据归并为可独立建 Trellis 任务的生产落地契约。它们不是当前代码已实现的功能清单：`reuse-existing` 表示沿用模板现有接缝，`candidate` 表示具备真实需求后可以立项，`defer` 表示只保留启动门槛。

## 能力导航

| 能力 | 当前决策 | prod 文档 | 主要来源 |
| --- | --- | --- | --- |
| IAM 与权限导航 | `reuse-existing` | [IAM 与权限导航](prod-iam-navigation.md) | RBAC、权限树、菜单与用户展示提交 |
| 配置、密钥、Redis 与分布式锁 | `reuse-existing` | [配置、密钥、Redis 与分布式锁](prod-config-secrets-redis-locks.md) | Redis、Fernet、Token 锁与启动配置提交 |
| 后端模块分层与依赖边界 | `reuse-existing` | [后端模块分层与依赖边界](prod-module-boundaries.md) | FileMonitor 解耦、依赖注入、CRUD 访问与 API 拆分提交 |
| 审计、请求关联与可观测性 | `reuse-existing` | [审计、请求关联与可观测性](prod-observability-audit.md) | ELK、日志、生命周期与启动提交 |
| Durable 异步投递 | `reuse-existing` | [Durable 异步投递](prod-durable-async.md) | Celery、邮件/FTP/通知任务提交 |
| 通用枚举与参考数据 | `candidate` | [通用枚举与参考数据](prod-reference-data.md) | 后端枚举 API 与前端枚举提交 |
| 文件导入、导出与安全存储 | `candidate` | [文件导入、导出与安全存储](prod-file-import-export.md) | DataFile、FTP、文件名与导入交互提交 |
| 文件监控与远程抓取安全 | `defer` | [文件监控与远程抓取安全](prod-file-monitor.md) | FileMonitor 拆分、Path Traversal、SSRF、ReDoS 提交 |
| 通知 Adapter | `defer` | [通知 Adapter](prod-notification-adapters.md) | WeCom、Token、重试接收人提交 |
| 事件回调与最小 Webhook | `candidate` | [事件回调与最小 Webhook](prod-event-callback-webhook.md) | 事件回调、条件与回调修复提交 |
| 审批工作流 | `defer` | [审批工作流](prod-approval-workflow.md) | 审批流、超时、并发、前端闭环提交 |
| 计划任务运行时 | `reuse-existing` | [计划任务运行时](prod-scheduler-runtime.md) | scheduled-task 全生命周期提交 |
| 服务通信 | `defer` | [服务通信](prod-service-communication.md) | 服务端点、链路查询与监控提交 |
| 外部集成中心 | `defer` | [外部集成中心](prod-external-integration.md) | Integration Center、事件路由与条件编辑提交 |
| 前端应用壳与交互韧性 | `reuse-existing` | [前端应用壳与交互韧性](prod-frontend-shell.md) | Tab、刷新、懒加载、剪贴板、导入反馈提交 |

## 统一 prod 要求

未来把任一 `candidate` 或 `defer` 能力变成代码前，必须新建独立任务，并明确：

- 领域所有权、数据模型、状态迁移和数据库约束；
- 服务端授权、租户边界、敏感数据脱敏和威胁模型；
- 幂等键、并发/租约、超时、重试、死信、人工恢复；
- 审计事件、Request ID/Trace、指标、日志和告警；
- 配置与密钥来源、迁移、兼容窗口、发布及回滚；
- 单元、集成、API、UI 和失败副作用验收。

提交级逐文件证据见 [能力矩阵](../capability-matrix.md)，旧版专题指南继续作为来源附录，不替代本目录的 prod 契约。
