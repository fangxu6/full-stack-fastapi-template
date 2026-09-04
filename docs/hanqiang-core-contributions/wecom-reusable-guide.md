# 企业微信（WeCom/WXWork）通知复用指南

本文把本仓库中与企业微信有关的后端、前端、审批通知、事件回调和异步任务经验汇总为一份可迁移蓝图。它不是某一次提交的逐行说明；每个结论都保留了对应的提交文档，便于回到 Git 快照核对历史行为。

## 1. 来源与能力范围

| 来源 | 可复用主题 |
| --- | --- |
| [4d916409：企业微信通知后端](backend-2025-12-02-4d916409.md) | 配置、卡片模板、发送日志/明细、管理 API、权限与审计模型。 |
| [48a982e4：企业微信通知前端](frontend-2025-12-02-48a982e4.md) | 配置/模板/日志管理页、类型化 API、菜单和路由权限。 |
| [5aaa334e：Token 分布式锁](backend-2025-12-03-5aaa334e.md) | 按配置锁刷新 Token、敏感日志收敛。 |
| [9158d8fe：Celery 异步边界](backend-2025-12-03-9158d8fe.md) | `log_id` 任务载荷、worker 独立事件循环与数据库会话。 |
| [eb990317：加密密钥演进](backend-2025-12-03-eb990317.md) | Fernet 密文版本、专用企业微信 key 与轮换边界。 |
| [75a213a7：配置加载](backend-2025-12-19-75a213a7.md) | YAML `wxwork` 子配置装配和环境注入注意事项。 |
| [5b65edac：过期 Token 重试](backend-2026-06-10-5b65edac.md) | 40001/40014/42001 白名单重试、stale Token 拒绝。 |
| [ff4db2d4：自定义接收人重试](backend-2026-06-10-ff4db2d4.md) | `original/custom_user_ids` 人工重试契约。 |
| [f68b3c8d：审批事件载荷](backend-2026-01-21-f68b3c8d.md) | `WXUserID`、审批链接、收件人解析和通知状态字段。 |
| [7c805e02：审批运维通知](backend-2026-01-26-7c805e02.md) | 催办、弃审、默认企微配置、模板卡 URL 兜底、通知状态同步。 |
| [事件回调平台](event-callback-platform-2026-01.md) | 配置驱动事件、internal/external/event 执行器和企业微信通知适配。 |
| [审批流复用指南](approval-flow-reusable-guide.md) | 审批事件码、事务边界、通知适配器和异步恢复规则。 |
| [7ba88a12：配置与加密](backend-2025-11-27-7ba88a12.md) | `wxwork.fernet_key`/全局密钥的配置优先级和密钥消费边界。 |
| [526927fb：启动会话](backend-2026-03-13-526927fb.md)、[72bda3f7：启动清理](backend-2026-04-02-72bda3f7.md) | 启动阶段企业微信模板初始化、数据库会话和多 worker 锁；预置写入不应混入每次启动。 |
| [5e048690：前端权限](frontend-2026-03-31-5e048690.md) | 企业微信配置/模板页面按钮权限接入统一权限候选集合。 |
| [36f0fda3：前端公共页面](frontend-2026-03-23-36f0fda3.md) | 现有企业微信配置、模板、发送日志页面在公共管理台中的位置。 |

这些资料共同覆盖“业务事件 → 通知载荷 → 企业微信模板 → Token → 渠道调用 → 审计/重试 → 前端查询”的完整链路。

## 2. 推荐总体架构

```text
业务模块/审批/事件回调
  -> NotificationService（模板编码、动态数据、收件人引用、幂等键）
  -> SendLog + Outbox 事务
  -> wxwork_send_message(log_id)
  -> Worker 按 log_id 重新读取配置/模板/快照
  -> TokenProvider（缓存 + 提前刷新 + 分布式锁）
  -> TemplateRenderer（结构化渲染 + 渠道 Schema 校验）
  -> WeComClient（gettoken / message/send）
  -> SendLog + SendAttempt 明细 + 业务通知状态
  -> 查询 API / 管理台轮询
```

建议保持以下职责边界：

| 层 | 职责 | 不应承担 |
| --- | --- | --- |
| 业务通知服务 | 选择模板、组装事件数据、确定收件人和幂等键。 | 读取 Secret、直接拼渠道 JSON。 |
| TokenProvider | 解密 Secret、缓存 Token、提前刷新、锁竞争处理。 | 发送业务消息或决定 HTTP 权限。 |
| 模板渲染器 | 变量校验、结构化替换、`template_card` Schema 校验。 | 直接调用企业微信。 |
| WeComClient | HTTP 请求、超时和响应解析。 | 数据库事务、无限重试。 |
| SendWorker | 领取日志、调用适配器、写 attempt、收敛状态。 | 信任过期任务 payload 或跨事件循环复用 session。 |
| API/管理台 | 认证、权限、配置/模板/日志操作和状态展示。 | 以按钮隐藏代替服务端授权。 |

业务模块应依赖稳定的 `NotificationService` 或 `WxWorkNotificationService`，而不是依赖管理 API 的 DTO。当前 CodeGraph 已确认审批、培训、APQP、文件监控、tooling 等多个消费者共用 `wxwork_notification_service.py`。

## 3. 配置、密钥与 Token 生命周期

### 3.1 配置数据

最小配置表（对应 `Sys_WXWork_Config`）应包含：

- `ConfigID`、唯一 `ConfigCode`、名称和 `AgentID`；
- 加密的 `Secret`；
- `AccessToken`、`TokenExpiredTime`、Token 版本/更新时间；
- `IsEnabled`、软删除和创建/更新审计字段。

列表、详情、操作日志和异常响应都不得返回 Secret 或可复用 Token。Secret 只在创建/更新写入边界出现，主密钥由 Secret Manager 或环境注入。

### 3.2 获取与缓存

`WXWorkConfigService.get_valid_token()` 的可复用规则是：Token 缺失、过期时间不可解析或剩余时间不超过安全窗口（当前 5 分钟）时调用 `refresh_token()`。`_fetch_token()` 使用企业微信 `expires_in` 计算过期时间，并统一应用时区。

刷新锁键应包含租户和配置：

```text
lock:{tenant_id}:wxwork:token:refresh:{config_id}
```

获锁后、未获锁时都必须重新读取数据库。锁竞争时只有确认缓存 Token 仍超过安全窗口才能返回；否则返回可重试的 503，而不是发送 stale Token。锁释放必须校验 owner token，不能无条件 `DEL`。

### 3.3 并发和故障边界

`5aaa334e` 的历史实现使用同步 Redis 锁、固定 TTL 和开发环境无锁降级；它是竞态修复参考，不是高并发生产模板。迁移时应：

- 异步请求路径使用异步 Redis 客户端，或将刷新放入同步 worker；
- TTL 覆盖最坏刷新耗时，必要时增加续租/fencing token；
- Redis 不可用时显式失败或告警，不能静默宣称已加锁；
- 以 Token 版本/更新时间条件写入，避免旧刷新响应覆盖新 Token；
- 记录刷新次数、锁等待、二次检查命中、剩余 TTL 和失败数。

## 4. 消息、模板与接收人

### 4.1 模板模型

对应 `Sys_WXWork_CardTemplate` 的最小字段：`TemplateCode`、`TemplateType`、结构化 `CardContent`、参数定义、版本、启用/删除标记。模板版本应在发送日志中快照或记录，保证后续可复现。

渲染必须先解析 JSON，再递归替换字符串值；不要把动态值直接拼接进 JSON 文本。发送前再按 `msgtype` 校验必填字段。当前实现对 `template_card` 会从 `ApprovalURL/DetailURL/approve_url/detail_url/url` 等动态字段提取兜底地址，补齐空的 `url` 和 `card_action.url`；迁移时应把 URL 作为显式必填契约，兜底只用于兼容历史模板。

### 4.2 接收人

统一输入模型可采用：

```json
{"individuals":["user-a"],"departments":[12]}
```

发送时去重并映射为企业微信 `touser`/`toparty`。审批通知从 `CommonUser.WXUserID` 解析收件人：直接审批人优先，角色成员兜底，过滤禁用/删除用户和空账号；流程管理员、发起人和节点审批人应由事件载荷明确区分。

服务端还需限制单次人数、校验 UserID/部门 ID 所属企业和启用状态，并在日志中保存收件人快照。不要把完整收件人写入普通日志。

### 4.3 发送响应分类

`errcode=0` 且没有 `invaliduser/invalidparty/invalidtag` 时为全部成功；存在无效目标时：

- 所有提供目标均无效：`FAILED`，消息未送达；
- 只有部分目标无效：`PARTIALLY_FAILED`，保留有效目标成功语义和无效目标摘要。

错误码、`errmsg`、`msgid`、attempt 和脱敏响应应写入主日志/明细。渠道已接受但响应超时不能直接判断失败，需进入 `unknown`/待核验状态，避免重复发送。

## 5. 发送日志、异步任务与幂等

### 5.1 持久化模型

建议保留两层记录：

- `SendLog`：一次逻辑发送的配置/模板/动态数据/接收人快照、状态、错误、重试策略和最终 `msgid`；
- `SendAttempt`：每一次实际渠道调用的时间、错误码、响应摘要、`msgid` 和发送状态。

状态至少区分 `PENDING`、`SENDING`、`SUCCESS`、`FAILED`、`PARTIALLY_FAILED`，并定义 `UNKNOWN` 或人工核验状态。状态更新要使用条件更新/租约，防止 worker、恢复任务和人工重试互相覆盖。

### 5.2 Celery 边界

API 先在事务内写入可查询日志，再投递 `wxwork_send_message(log_id)`。worker 在自己的事件循环内创建 engine/session/client，按 ID 重读配置、模板和快照，处理完成后关闭资源。不要把 AsyncSession、ORM lazy relation、Future 或 HTTP client 放进任务 payload。

历史 `9158d8fe` 仍存在“提交与 broker 发布分两步”的非原子边界；生产复用应采用 transactional outbox 或 pending 恢复扫描。`202 Accepted` 只表示持久化任务已受理，不表示企业微信已经送达。

任务失败时必须：

1. 将仍处于 `SENDING` 的日志收敛为可重试或失败；
2. 记录脱敏错误和 attempt；
3. 让 Celery 状态与业务终态一致；
4. 对 broker 不可用、worker 丢失和 outbox 未发布提供补偿。

## 6. Token 失效与人工重试

### 6.1 Token 失效

`5b65edac` 将 `40001`、`40014`、`42001` 归入可重试 Token 错误。发送第一次收到白名单错误后，强制刷新一次并使用同一消息体重发一次；刷新失败或第二次仍失败时停止，不得递归重试。其它错误码不应套用 Token 刷新逻辑。

### 6.2 自定义接收人

`ff4db2d4` 新增：

```json
{"retry_mode":"original"}
```

```json
{"retry_mode":"custom_user_ids","custom_user_ids":["user-a","user-b"]}
```

`original` 模式在部分失败时可依据 `invaliduser/invalidparty` 缩小接收人；无法解释时保留原配置。`custom_user_ids` 会完全替换原接收人，只保留清洗、去重后的 UserID。路由使用 `wxwork:send-log:resend` 权限并返回 202，最终状态由 `log_id` 查询。

当前历史实现会把人工重试的 `RetryCount` 重置为 0；严格审计场景应改为单调计数、增加 `RetryGeneration` 或新建逻辑发送记录。人工重试必须保留原/新接收人、操作者、原因和时间，不能覆盖历史 attempt。

## 7. 审批、事件回调与企业微信桥接

### 7.1 审批事件

审批事件载荷（见 `f68b3c8d`）应包含流程/节点/工作流 ID、业务编码、操作者、状态、时间、`ApprovalURL`/`DetailURL`/`EditURL`/`ResubmitURL` 和 `RecipientWXUserIDs`。推荐事件码：

`approval_process_started`、`approval_node_assigned`、`approval_node_approved`、`approval_process_returned`、`approval_process_rejected`、`approval_process_completed`、`approval_process_cancelled`、`approval_process_abandon`、`approval_process_resubmitted`。

审批服务只发布通用事件；企业微信由 Notification Adapter 消费。这样同一事件可以同时支持邮件、站内信或其它渠道。

### 7.2 催办与操作日志

审批催办先写 `Approve_Process_OperationLog(NotifyStatus=1)`，再派发企业微信任务；worker 完成后按 `WXSendLogID` 同步：`2=发送中`、`3=成功`、`4=失败`，失败信息来自最新发送 attempt。催办必须有 1 小时冷却、收件人去重和权限校验，发送失败不能回滚已经提交的审批动作。

### 7.3 事件回调平台

事件平台的 internal/external/event 执行器可以把企业微信适配器作为一个通知消费者。事件配置应按事务类型、目标工作流和条件匹配，日志保存 `TraceID`、执行状态、级联深度和脱敏响应。回调发布失败不回滚主审批事务，依靠回调日志和恢复任务补偿。

### 7.4 配置加载、模板初始化与前端权限

- 配置加载器支持 `wxwork` 子配置；生产环境应由 Secret Manager/环境变量注入 `corp_id`、`agent_id`、Secret 和 Fernet/KMS key。`config.yaml` 只保留示例键名，不能提交真实凭证。
- `wxwork.fernet_key` 可作为企业微信专用密钥，缺失时按项目约定回退全局 `encryption_key`；必须由唯一加密提供者实现并记录 key 版本，不能让各模块各自猜测优先级。
- 启动阶段可以幂等创建企业微信默认模板（当前初始化服务为 `wxwork_template_init_service.ensure_templates`），并用数据库锁避免多 worker 重复执行；模板初始化失败是否阻止启动需显式定义。
- 移除其它业务预置数据的启动写入时，不要误删企业微信模板初始化、RBAC 或会话基础设施；一次性 seed 应拆成可审计的部署命令或迁移步骤。
- 前端 `ConfigManagement.vue`、`TemplateManagement.vue` 的按钮权限应来自统一权限候选集合；菜单隐藏不能替代后端 `wxwork:config:*`、`wxwork:template:*`、`wxwork:send:*` 和 `wxwork:send-log:*` 校验。

## 8. 管理台前端契约

复用前端可拆成三页和一个服务层：

| 页面/模块 | 责任 |
| --- | --- |
| `ConfigManagement.vue` | 配置元数据、一次性 Secret 输入、连接测试、启停和软删除。 |
| `TemplateManagement.vue` | JSON 卡片编辑、参数提示、版本和渲染预览；预览不等于发送。 |
| `SendLogQuery.vue` | 过滤、详情、attempt、状态轮询和受控人工重试。 |
| `src/services/wxwork.ts` + `src/types/wxwork.ts` | 统一 URL、响应壳、分页、状态和重试请求类型。 |

路由/菜单可采用 `menu:wxwork_config`、`menu:wxwork_template`、`menu:wxwork_send_log` 等 feature key，但后端仍必须独立保护配置读取、模板写入、发送、日志详情和重试。读 DTO 与写入 DTO 分离，Secret 不得出现在读类型中。

日志页应遵循：提交后显示“已受理（log_id）”→ 查询/轮询 → 展示最终状态；网络超时不能自动再次发送。敏感错误详情、原始动态数据和自定义接收人需单独权限、脱敏和审计。

## 9. 安全与运维验收

- [ ] Secret、Fernet/KMS 主密钥、Token、Authorization、动态数据、完整消息体和完整收件人不进入普通日志或 API 响应。
- [ ] 配置和模板启用/软删除状态在 API、worker、人工重试和默认配置懒创建时重新校验。
- [ ] Token 锁按租户/配置隔离；锁竞争不会使用 stale Token，锁释放不会误删他人锁。
- [ ] 40001/40014/42001 只触发一次刷新重试；网络超时有 unknown/核验策略。
- [ ] 每次渠道调用都有 attempt；主日志不会永久停在 `SENDING`，人工重试不覆盖历史计数和审计。
- [ ] API 202、Celery 状态、业务终态、outbox 发布状态分别可观测，存在恢复扫描或补偿任务。
- [ ] `invaliduser/invalidparty/invalidtag` 的全部失败、部分失败和成功语义有自动化覆盖。
- [ ] 审批通知的 `WXUserID`、链接、冷却、`NotifyStatus` 和 `WXSendLogID` 可追踪；通知失败不回滚主审批事务。
- [ ] 模板渲染对引号、换行、URL、未知变量和缺失必填字段有测试；渲染预览不会调用真实发送接口。
- [ ] 管理台按钮权限与后端权限一致，跨租户 UserID、日志和配置访问会被服务端拒绝。

## 10. 迁移顺序

1. 先落地配置/模板/SendLog/Attempt 表和加密提供者，完成空库 migration 与密钥轮换方案。
2. 实现 WeComClient、TokenProvider 和结构化模板渲染器，先用单元测试验证错误分类与 URL 契约。
3. 用 outbox + `log_id` worker 接通真正异步发送，加入租约、恢复扫描和幂等键。
4. 再接入审批/事件回调 Notification Adapter，统一 `WXUserID`、链接和通知状态同步。
5. 最后接入管理台页面、轮询、日志详情和人工重试；前端只消费领域 DTO。
6. 用真实企业微信沙箱、Redis、broker、测试数据库和至少两个 worker 演练 Token 竞争、重复投递、渠道超时、人工重试和密钥轮换。

## 11. 当前代码复核入口

```bash
rtk codegraph explore "get_valid_token refresh_token get_access_token process_send_by_log_id handle_send_result"
rtk codegraph explore "retry_send_log SendLogRetryRequest WXWorkLogService.retry"
rtk codegraph explore "WxWorkNotificationService.send_template_card sync_notify_status_by_wx_send_log_id"
rtk codegraph node backend/JSECommon/app/services/wxwork/config_service.py
rtk codegraph node backend/JSECommon/app/services/wxwork/send_service.py
rtk codegraph node backend/JSECommon/app/services/wxwork/log_service.py
rtk codegraph node backend/JSECommon/app/tasks/wxwork_tasks.py
```

历史提交复核：

```bash
rtk git -C backend/JSECommon show --stat --summary --format=fuller 5b65edac
rtk git -C backend/JSECommon show --stat --summary --format=fuller ff4db2d4
rtk git -C backend/JSECommon show 4d916409 -- app/models/wxwork app/schemas/wxwork app/services/wxwork app/api/v1/routes/wxwork
rtk git -C frontend/JSE_UI_AI show 48a982e4 -- src/types/wxwork.ts src/services/wxwork.ts src/pages/wxwork
```
