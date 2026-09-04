# 事件回调平台：配置驱动的事件分发、执行与审计

> 合并来源：hanqiang 在 backend/JSECommon 与 frontend/JSE_UI_AI 的 6 个提交。  
> 适用场景：把业务事件转换为可配置的内部调用、外部 HTTP 回调或级联事件，并提供顺序执行、重试、审计和运维恢复能力。  
> 复核方式：Git 提交统计 + CodeGraph 当前调用关系；文档中的路径以当前仓库结构为准。

## 1. 主题结论

这组提交把原先耦合在 DataFile 中的 callback 能力抽成系统级事件平台：

1. 事件配置决定何时触发，回调配置决定按什么顺序执行。
2. EventDispatcher 只负责匹配、建日志和投递首个任务，不在业务请求中执行回调。
3. callback_worker 通过执行器 Registry 处理 internal、external、event 三类动作。
4. 每个回调都有 Sys_Event_Log 审计记录，后续回调在前置回调成功后顺序推进。
5. 事件上下文携带 trace_id、级联深度和执行堆栈，用于去重、追踪和防止循环。
6. 前端以条件编辑器、变量/模板编辑器、配置页和日志页提供完整配置闭环。

迁移到其他项目时，应把它视为一个独立平台模块，而不是复制若干 API 页面。数据库、消息队列、权限、执行器白名单和审计策略必须同时落地。

## 2. 提交时间线与 Git 范围

| 日期 | 仓库 | 提交 | 作用 |
| --- | --- | --- | --- |
| 2026-01-04 | backend/JSECommon | 72589c6453fdb3fec235d0844bd4a2494ba86b96 | 后端事件模型、CRUD、调度器、执行器、Worker、企业微信通知和 DataFile callback 迁移初版 |
| 2026-01-04 | frontend/JSE_UI_AI | 88d8a596c9c2135333806b63ef6368e5fb5ff0d7 | 事件配置、回调配置、事件日志页面与通用编辑组件初版 |
| 2026-01-06 | backend/JSECommon | 66ae2419ce1dd1df962aad90d0eeb5a8de6c14b7 | 调度器/Worker 完善、事件调试 Schema、API 规范和文件监控接收历史链路调整 |
| 2026-01-06 | frontend/JSE_UI_AI | 9c55b00ba5d3055292a9112d809c887f349e545d | 条件与执行模板交互完善、事件日志查询和组件测试补齐 |
| 2026-01-07 | backend/JSECommon | 0b5f74b522f2912043b6505bcf32e9cc8015a8c9 | 外部 URL 安全边界统一到 url_validator.validate_url() |
| 2026-01-07 | backend/JSECommon | 8950f544cca478df934ae8b6c691b737d2792441 | 修复审查发现的 16 个问题：异常、状态、Registry、协议、级联、脱敏和队列统一 |

提交统计显示，初版后端涉及 49 个文件，前端涉及 22 个文件；0b5f74b5 修复涉及 2 个文件，8950f544 修复涉及 19 个文件。coverage.xml 等生成物随提交变化，不应作为平台迁移内容。

## 3. 涉及文件地图

### 3.1 后端公共层

| 能力 | 当前文件 | 迁移职责 |
| --- | --- | --- |
| API | app/api/v1/routes/event/__init__.py、event_config.py、event_callback.py、event_log.py | 配置、回调、日志的 CRUD/查询/重放/调试边界 |
| 契约 | app/schemas/event/event_config.py、event_callback.py、event_log.py、event_debug.py | 请求校验、分页、调试触发和响应结构 |
| 数据模型 | app/models/event/event_config.py、event_callback.py、event_log.py | Sys_Event_Config、Sys_Event_Callback、Sys_Event_Log 映射 |
| 数据访问 | app/crud/event/crud_event_config.py、crud_event_callback.py、crud_event_log.py | 基础查询、写入、分页和状态更新 |
| 业务服务 | app/services/event/event_config_service.py、event_callback_service.py、event_log_service.py | 唯一性、软删除、排序、操作日志和日志运维 |
| 分发 | app/services/event/event_dispatcher.py | 事件匹配、条件判断、去重、日志提交、首任务投递 |
| 条件/模板 | condition_evaluator.py、template_resolver.py | 场景条件、触发条件和 messageSchema 渲染 |
| 执行器 | executors/base.py、internal_executor.py、external_executor.py、event_executor.py、registry.py | 统一动作契约、白名单内部调用、HTTP 调用和级联事件 |
| 解耦协议 | app/services/event/protocols.py | EventExecutor 依赖 EventPublisher 协议，而非具体调度器 |
| 异步任务 | app/tasks/callback_worker.py、event_recovery_tasks.py | 单条日志执行、顺序推进、失败恢复、死信处理 |
| 共享常量/异常 | app/constants/event.py、app/exceptions/event.py | 执行状态、队列名、默认级联深度和领域异常 |
| 安全工具 | app/utils/url_validator.py、path_validator.py、log_payload_sanitizer.py、uuid_utils.py | URL/路径边界、敏感字段脱敏和 UUID 转换 |
| 基础设施 | app/core/celery_app.py、app/core/api_spec.py、start_celery_worker.sh、check_celery.sh | 队列注册、API 文档元数据和 Worker 启动检查 |
| 兼容迁移 | app/tasks/datafile_tasks.py、app/services/datafile/**、app/services/file_monitor/** | 旧 DataFile callback 迁移到统一事件链，文件监控接收历史继续发布事件 |
| 接口文档 | docs/api/event.md | 事件 API 与调试接口说明 |

### 3.2 前端公共层

| 能力 | 当前文件 | 迁移职责 |
| --- | --- | --- |
| 条件编辑 | src/components/event/ConditionEditor.vue | 表格模式与 JSON 模式互转，编辑 field/op/value |
| 执行模板 | src/components/event/ExecutionTemplateEditor.vue | internal、external、event 三类执行器配置和 JSON 预览 |
| 变量选择 | src/components/event/VariableSelector.vue | 从事件数据选择字段或 JSONPath |
| 日志详情 | src/components/event/EventLogDetail.vue | 单条执行日志和响应信息展示 |
| 管理页面 | src/pages/event/EventConfigManagement.vue、CallbackConfigManagement.vue、EventLogQuery.vue | 配置、回调排序/启停、日志查询、Trace/死信查看 |
| API 服务 | src/services/event/eventConfigService.ts、callbackConfigService.ts、eventLogService.ts | 与后端契约对应的请求封装 |
| 类型 | src/types/event.ts、src/types/event/index.ts | 配置、模板、日志、执行状态和查询类型 |
| 应用接入 | src/router/index.ts、src/components/layout/AppSidebar.vue | 路由、菜单和权限入口 |
| 测试 | src/components/event/__tests__/ConditionEditor.test.ts、ExecutionTemplateEditor.test.ts | JSON 解析、组件同步和模板编辑回归 |

## 4. 端到端调用链

~~~text
业务服务
  -> EventDispatcher.publish(event_code, event_data, trace_context)
     -> 查询启用且未删除的 Sys_Event_Config
     -> 匹配 TransactionType / TargetObjectType
     -> 评估 ScenarioConditions
     -> 查询启用的 Sys_Event_Callback，并按 CallbackOrder 排序
     -> 评估 TriggerCondition
     -> 以 (ConfigID, CallbackID, TraceID) 去重
     -> 创建 Sys_Event_Log(pending)，记录 EventData/Trace/级联上下文
     -> 提交数据库事务
     -> send_task("event.process_callback_log", queue="event_callback")
  -> callback_worker.process_callback_log(log_id)
     -> 读取日志和回调配置
     -> Registry.get(execution_type)
     -> 执行 internal / external / event
     -> 更新执行状态、响应、耗时和脱敏错误
     -> 当前回调成功后投递同配置的下一个回调
     -> 失败时进入恢复扫描或死信
~~~

### 4.1 EventDispatcher 的核心边界

- publish() 接收 event_code、event_data、异步数据库会话和可选 trace_context，返回 matched/scheduled/dispatched/trace_id。
- 事件配置先按 EventCode、启用标记和软删除标记过滤，再匹配交易类型、目标对象和场景条件。
- TargetObjectType=APPROVAL_FLOW 时支持按 WorkflowID 绑定具体流程；专属配置产生日志后不再触发同事件码全局配置，否则回退到全局配置。
- trace_context 支持 trace_id、cascade_depth、creator_id、execution_stack、skip_callback_ids 和 dedupe_key。
- 数据库提交在 Celery 投递前完成。投递失败保持日志为 pending，由恢复任务重试消息交接。
- 只投递每个回调链的第一个可执行日志，后续日志由 Worker 在前置成功后推进，避免并行打乱 CallbackOrder。
- debug_publish_config() 可以指定配置或单条回调触发，并默认仍评估条件；force 只能在受控调试权限下开放。

### 4.2 日志与状态

Sys_Event_Log 至少应保存：

| 字段 | 作用 |
| --- | --- |
| LogID | 单次回调执行标识，也是 Celery 任务参数 |
| ConfigID / CallbackID | 反查配置和执行器 |
| TraceID | 一次业务事件及其级联链路的关联键 |
| EventData | 事件快照；需按敏感数据策略脱敏或加密 |
| ExecutionStatus | pending、执行中、成功、失败等统一状态 |
| ResponseCode / ResponseData | 外部响应或内部执行摘要；需截断并脱敏 |
| ErrorMessage | 可观测错误；禁止写入 token、密码和完整请求体 |
| ExecutionTime | 执行耗时或时间戳，需与 API 契约统一单位 |
| CascadeDepth / ExecutionStack | 级联限制、循环检测和调试 |
| IsInDeadLetter | 标记是否进入死信，避免恢复任务重复投递 |
| CreatorID、时间字段 | 审计和租户/用户归属 |

状态更新必须带当前状态条件或版本号，确保 Worker 重试、恢复扫描和人工重放不会互相覆盖。

## 5. 执行器契约

### 5.1 通用执行器

CallbackExecutor 是执行器基类；执行器接收回调配置和事件日志上下文，返回可序列化的执行结果或抛出领域异常。registry.py 提供：

- 注册：按稳定的 execution_type 注册实现；
- 获取：Worker 不再通过 if/elif 硬编码执行器；
- 列出：管理端或启动检查可用于能力发现；
- 初始化：默认注册 internal、external、event，需保证多进程初始化幂等。

注册表是模块级全局对象，测试时应清理或使用隔离注册表；生产环境启动时应记录最终注册的类型列表。

### 5.2 internal

- 通过内部服务白名单映射调用既有业务服务。
- 不允许前端提交任意 Python import 路径、模块名或函数名。
- 参数通过 TemplateResolver.build_payload() 从事件数据构建，内部服务自行做领域校验。
- 内部调用需要透传 trace_id、creator_id 和租户上下文，避免级联事件丢失来源。

### 5.3 external

- 配置包含 URL、HTTP 方法、headers、bodyTemplate、超时和重试参数。
- headers/body 使用模板解析，可取 literal、fieldName 或轻量 JSONPath（如 $.a.b[0].c）。
- 文件名字段支持追加文本且保持多重后缀，例如 report.xlsx 追加 _done 后得到 report_done.xlsx。
- URL 在后端再次通过 url_validator.validate_url() 校验，不能只依赖前端。
- 重试可能重复提交业务请求；默认只重试明确幂等的操作，其他请求必须携带业务幂等键或禁用自动重试。

当前 URL 校验属于局域网场景的简化 SSRF 防护：允许 HTTP、支持域名通配符，只拦截有限危险 IP。迁移到不可信网络前，还要补充 DNS 多地址、IPv6、端口白名单、重定向复查、DNS rebinding 防护和出站网络隔离。

### 5.4 event

- 使用 EventPublisher Protocol 发布下一个事件，避免执行器依赖具体 EventDispatcher 实例。
- 级联深度达到默认上限（当前为 5）或事件已在执行堆栈中时拒绝继续级联，并记录 CascadeException。
- skip_callback_ids 用于已执行回调的跳过；trace 和堆栈长度应设置上限，防止事件链膨胀。
- 级联发布仍需经过正常配置、条件、权限和审计路径，不应提供绕过校验的快捷入口。

## 6. 模板与条件数据契约

### 6.1 messageSchema

后端 TemplateResolver 以输出字段为键，每个字段至少包含 source：

~~~json
{
  "title": {
    "source": "literal",
    "value": "审批结果"
  },
  "workflow_id": {
    "source": "fieldName",
    "value": "WorkflowID",
    "required": true
  },
  "items": {
    "source": "$.BODY.DATA[0].RESULT",
    "required": false
  },
  "file_name": {
    "source": "fieldName",
    "value": "FileName",
    "append": "_processed",
    "append_keep_suffix": true
  }
}
~~~

支持规则：

- literal：直接使用 value；
- fieldName：按点号访问事件字典；
- $.jsonpath：当前为轻量点号/数组下标访问，不是完整 JSONPath；
- required=false 且取值不存在时输出 null，否则使用缺省值；
- append 支持 ${value}、${NOW}、${NOW_YYYYMMDDHHMMSS} 和事件字段占位符；
- 输出键支持点号嵌套，例如 dynamic_data.file_name；
- 文本、列表、字典会按 JSON 规则转为文本，目标项目应明确 API 的类型保留策略。

TemplateResolver.build_payload() 当前没有 CodeGraph 找到的直接覆盖测试，迁移时至少补齐字段缺失、数组越界、恶意模板、文件名后缀和嵌套输出测试。

### 6.2 条件模型

ConditionEditor.vue 提供条件行与 JSON 双向编辑；后端 condition_evaluator.py 是最终判定边界。应统一：

- 支持的操作符集合及空值语义；
- 字段路径格式；
- 字符串/数字/布尔类型转换；
- 条件异常是拒绝触发还是返回不匹配；
- 前端仅做编辑体验，不能代替后端校验。

## 7. 前端复用方式

推荐将前端分成三层：

1. 纯编辑组件：复制 ConditionEditor、VariableSelector、ExecutionTemplateEditor，通过 v-model 接收后端契约，不在组件内直接请求 API。
2. 领域页面：配置页负责事件配置，回调页负责执行器和顺序，日志页负责 Trace/状态/死信查询。
3. 服务与类型：将 src/services/event/* 和 src/types/event.ts 作为唯一 API 类型源，路由和菜单只负责接入权限。

当前 ExecutionTemplateEditor 已覆盖：

- 内部白名单服务选择；
- 外部 URL、方法、headers、bodyTemplate、timeout、maxRetries；
- messageSchema 字段编辑和 JSON 预览；
- literal、fieldName、JSONPath 数据来源；
- 调试延迟和 pre_commit_blocking 同步策略；
- 保留未完成的草稿行；
- 事件配置下拉中的禁用/未知项提示。

迁移时要统一 timeout 单位。当前 internal/external 代码路径存在单位差异风险，不能让前端字段名掩盖后端实际单位。

## 8. 队列、恢复与事务设计

- 队列名集中为 EVENT_CALLBACK_QUEUE = "event_callback"，Worker 启动脚本和检查脚本必须使用同一常量。
- Worker 任务在 Celery 进程内创建异步数据库连接，当前采用 NullPool，任务结束释放连接；高吞吐部署可改由 PgBouncer/ProxySQL 承担连接池。
- 日志先提交、消息后投递不是分布式事务。必须保留 pending 恢复扫描，或迁移为 Outbox + 独立发布器。
- 恢复任务只处理符合状态、重试次数和时间窗口的日志；进入死信后不得被普通恢复任务再次投递。
- 人工重放应生成新的尝试记录或带幂等键，保留原日志和操作者审计，不要直接覆盖历史结果。
- 顺序回调必须以数据库状态为准推进；Worker 重试时要能识别已完成的前置步骤。

## 9. 安全、可靠性与可观测性边界

迁移验收不能只看“页面能保存、任务能执行”，至少检查以下风险：

| 风险 | 当前实现/限制 | 迁移要求 |
| --- | --- | --- |
| SSRF | 简化 URL 校验，HTTP/通配域名仍可用 | 出站代理或网络隔离；校验解析后的全部地址、端口和重定向 |
| 重试副作用 | external 重试可能重复写入 | 幂等键、幂等接口或按方法禁用重试 |
| 数据库/队列不一致 | 提交与投递分两步 | 保留恢复扫描，优先演进 Outbox |
| 并发状态覆盖 | Worker、恢复、重放可能同时更新 | 条件更新/乐观锁/幂等状态机 |
| 级联爆炸 | 默认深度 5，仍需控制上下文大小 | 深度、堆栈、Trace 长度上限和循环告警 |
| 执行器逃逸 | internal 必须白名单 | 禁止任意导入、动态执行和前端自定义 callable |
| 敏感数据 | EventData、请求/响应、headers 可能含凭证 | 字段级脱敏、长度截断、加密/保留期和访问审计 |
| 调试绕权 | debug_publish_config(force=True) 能跳过条件 | 独立权限、审计、速率限制和生产禁用策略 |
| 目标类型扩展 | 当前主要支持 APPROVAL_FLOW，其他类型保守不匹配 | 用显式能力注册表扩展，避免静默误触发 |
| 前后端边界 | 前端可编辑 URL/headers/body | 后端重新校验并记录拒绝原因 |
| 可观测性 | Trace/状态/死信已有基础字段 | 指标至少覆盖匹配数、投递失败、执行耗时、重试、死信和级联拒绝 |

## 10. 推荐的跨项目模块拆分

先复制最小闭环，再按需要增加适配器：

~~~text
event_platform/
  domain/
    models.py              # config/callback/log
    exceptions.py
    protocols.py
  application/
    dispatcher.py
    condition_evaluator.py
    template_resolver.py
    log_service.py
  executors/
    base.py
    registry.py
    internal.py
    external.py
    cascade.py
  adapters/
    sqlalchemy_repositories.py
    celery_worker.py
    auth_and_audit.py
    outbound_http.py
  api/
    config_routes.py
    callback_routes.py
    log_routes.py
~~~

建议先实现 external 之外的 dry-run 和日志查询，再接入真实出站 HTTP；这样可以先验证事件匹配、模板、顺序和恢复机制。

## 11. 跨项目迁移清单

### 后端

- [ ] 建立三张事件表及索引：EventCode、ConfigID、CallbackID、TraceID、状态和创建时间。
- [ ] 明确软删除、启停、唯一性（EventCode + ScenarioName）和回调排序约束。
- [ ] 接入项目统一的认证、租户、权限和操作日志。
- [ ] 注册 event_callback 队列并验证 Worker/Beat 启动配置。
- [ ] 将内部服务映射到白名单；禁止运行时任意导入。
- [ ] 为外部 HTTP 设置出站网络策略、URL/端口/重定向校验和超时单位。
- [ ] 实现 pending -> running -> success/failed/dead_letter 幂等状态机。
- [ ] 实现恢复扫描、死信查询、人工重放和取消语义。
- [ ] 限制事件数据、请求体、响应体、headers、Trace 和执行堆栈大小。
- [ ] 为模板解析、条件评估、顺序执行、重复投递和级联循环补测试。

### 前端

- [ ] 复用三个编辑器组件，但通过项目 API 类型重新约束字段和操作符。
- [ ] 配置页与回调页按权限拆分，隐藏无权执行器和调试入口。
- [ ] 日志页支持按 Trace、状态、时间、配置和死信筛选。
- [ ] 对未知/禁用事件配置显示明确状态，不静默提交失效 ID。
- [ ] 统一 timeout、重试次数和同步策略的单位/枚举。
- [ ] 编辑器保留 JSON 高级模式，但提交前显示后端校验错误。

### 运维与验收

- [ ] 用一个真实业务事件验证：配置匹配、条件不匹配、首条投递、后续顺序和日志查询。
- [ ] 手动让 Broker 投递失败，确认日志保持 pending 并可恢复。
- [ ] 让外部服务超时/返回 5xx，确认重试、幂等键和死信行为。
- [ ] 构造相同 TraceID 重复发布，确认不会重复创建回调日志。
- [ ] 构造级联循环和超过深度的链，确认拒绝且有审计。
- [ ] 在日志中确认 token、密码、Cookie、Authorization 和完整请求体已脱敏。
- [ ] 对 debug 接口执行无权限、强制跳过条件和速率限制测试。

## 12. CodeGraph/Git 复核命令

在本仓库中：

~~~bash
rtk codegraph explore "EventDispatcher publish callback_worker ExternalExecutor InternalExecutor TemplateResolver EventConfigService"
rtk codegraph explore "TemplateResolver build_payload ConditionEditor ExecutionTemplateEditor EventLogQuery event.process_callback_log event_recovery"
rtk git -C backend/JSECommon show --stat --oneline 72589c64 66ae2419 0b5f74b5 8950f544
rtk git -C frontend/JSE_UI_AI show --stat --oneline 88d8a596 9c55b00b
rtk git -C backend/JSECommon show --name-status 8950f544
rtk git -C frontend/JSE_UI_AI show --name-status 9c55b00b
~~~

复用到新项目时，先用 CodeGraph 追踪 publish() 的所有调用者，再确定事件代码、事件数据结构和权限边界；不要只按文件名复制实现。

## 13. 来源文档

本文件合并并替代以下 6 份提交摘要：

- backend-2026-01-04-72589c64.md
- backend-2026-01-06-66ae2419.md
- backend-2026-01-07-0b5f74b5.md
- backend-2026-01-07-8950f544.md
- frontend-2026-01-04-88d8a596.md
- frontend-2026-01-06-9c55b00b.md
