# Hanqiang 事件能力 Deferred Iterations

## Purpose

本任务先交付不依赖具体业务的事件回调内核。具体业务事件、出站 Webhook 和其它执行器必须在真实消费者与外部契约明确后单独立项。

## Traceability Rules

- 延期项目不计入当前内核的验收标准。
- 每个延期项目必须新建独立 Trellis 任务，并提供自己的 PRD、design、implement 和适用的 E2E 计划。
- 不通过占位 API、动态配置 UI、宽松 fallback 或假业务数据提前暴露延期流程。

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
|---|---|---|---|---|
| D-001 | 具体业务事件适配器 | 当前没有确认的领域事件和业务所有者 | 事件信封与发布协议稳定 | 业务事件契约、快照、权限、幂等和集成验收 |
| D-002 | 最小出站 Webhook | 需要真实外部消费者、URL/Secret 策略和接收方幂等契约 | D-001、事件投递内核 | Webhook Adapter、SSRF 防护、签名、重试、投递查询和人工重放 |
| D-003 | 动态回调配置与管理 UI | 没有多个消费者和稳定字段目录时会形成猜测性平台 | D-001、至少两个真实消费者 | 版本化订阅、白名单条件、权限菜单、生成 client 和 UI 验收 |
| D-004 | 内部/级联执行器 | 需要明确跨模块副作用和循环控制需求 | D-001、事件执行协议 | 白名单执行器、级联深度/堆栈限制和跨模块审计 |

## Suggested Iteration Order

D-001 -> D-002；D-001 -> D-003；D-001 -> D-004。D-002、D-003、D-004 之间没有强制依赖。

## Remaining Work In Current Scope

事件信封、事务内登记、投递状态、处理协议、租约/幂等/恢复、审计与测试假执行器仍属于当前任务，不能因延期 Adapter 而省略。
