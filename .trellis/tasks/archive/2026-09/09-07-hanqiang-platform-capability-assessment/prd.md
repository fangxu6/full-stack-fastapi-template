# 评估 hanqiang 文档中的平台能力引入

## Goal

基于 `docs/hanqiang-core-contributions/` 与当前模板代码，形成一份可长期复用的平台能力引入评估，回答哪些能力值得进入模板、应如何分期、哪些内容应保持为业务适配器。

## Background

- 当前模板已经具备 IAM、`AuditEvent`、带租约和重试的 `EmailOutbox`、Celery/Redis，以及 Scheduler 任务和执行记录。
- 当前代码未发现事件回调内核、审批服务、外部集成中心、Webhook、服务通信管理或 WeCom 适配器。
- hanqiang 文档中的能力来自另一套业务系统，不能仅按提交标题复制；必须区分可迁移契约和领域耦合实现。

## Requirements

1. 建立文档能力矩阵，标记当前已存在、可复用、需要新增和暂不引入的能力。
2. 以平台底座定位评估事件回调、外部 HTTP 集成和审批流的依赖、边界、分期顺序与风险。
3. 明确现有 IAM、审计、邮件 Outbox、Scheduler、Celery 的复用接缝，禁止重复建设。
4. 给出后续实施的可观察验收门槛，包括状态一致性、幂等、权限、敏感数据、SSRF 和恢复机制。
5. 本任务只产出 Markdown 评估文档，不修改业务代码、数据库迁移、OpenAPI 或前端功能。

## Out of Scope

- 实现事件发布器、Webhook、外部集成中心或审批流。
- 搬运 WeCom、服务通信、文件监控等强业务/强部署能力。
- 对 hanqiang 提交逐条重写或复制其目录结构。

## Acceptance Criteria

- [x] `docs/hanqiang-platform-capability-assessment.md` 说明现有能力、缺口、候选能力和分期路线。
- [x] 报告明确推荐“事件回调 → 外部集成 → 审批流”的评估顺序，并说明取舍依据。
- [x] 每个主要结论同时有当前代码路径或 hanqiang 文档依据。
- [x] 报告列出后续实施的接口/状态/安全/运维验收门槛，但不伪装为已实现能力。
- [x] 工作区检查确认本任务没有业务代码或迁移变更。
