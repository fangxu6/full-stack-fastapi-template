# hanqiang 平台能力引入评估

> 状态：全量评估完成，未实施运行时代码。
> 事实源：`docs/hanqiang-core-contributions/` 下的提交级文档、当前模板源码、`.trellis/spec/` 和 [全量能力矩阵](hanqiang-core-contributions/capability-matrix.md)。

## 范围与证据

本轮逐文件复核目录中的 98 个提交级文档：后端 59 个、前端 39 个；另有 7 个历史汇总/复用指南。矩阵每行保留原始文件、SHA、主题、能力归属、复用结论、风险、决策和 prod 文档映射，没有用旧总索引的 94 条计数替代实际文件清单。

矩阵决策统计如下：

| 决策 | 行数 | 含义 |
| --- | ---: | --- |
| `reuse-existing` | 42 | 当前模板已有接缝，只吸收契约、边界和验收要求 |
| `candidate` | 16 | 有真实消费者后可独立建任务实施 |
| `defer` | 40 | 有价值但缺少消费者、外部契约或前置安全能力 |

历史业务字段、FT/PMS 专属场景、页面展示细节和任意执行器没有升级成独立平台能力；它们只在矩阵中作为来源证据或风险说明保留。

## 当前模板基线

| 能力 | 当前事实 | 评估动作 |
| --- | --- | --- |
| IAM、RBAC、路由授权 | 已有 `backend/app/models/iam.py`、`backend/app/modules/iam/`，前端有集中 guards/navigation/permission helpers | 复用，不重建权限系统 |
| 审计与请求关联 | 已有 `AuditEvent`、Request ID 和统一异常/日志链路 | 复用为所有未来能力的审计出口 |
| 异步投递 | 已有 `EmailOutbox`、Celery；Worker 重新读取数据库事实 | 复用 Outbox、租约、重试原则，不把 Broker 确认为业务完成 |
| 计划任务 | 已有 `SchedulerJob`/`SchedulerRun` 和调度模块 | 复用运行时，不搬运另一套通用 Scheduler |
| 配置、密钥、Redis、锁 | 已有配置和基础运行时接缝；具体密钥/缓存策略按能力约束 | 复用现有边界，补 fail-fast、TLS、TTL 和轮换要求 |
| 文件与库存基础能力 | 已有局部导入/导出和库存纠错模块 | 不据此宣称已有通用文件平台或审批内核 |
| 前端应用壳 | 已有 `app/*`、`platform/*`、`features/*`、`shared/*` 分层、集中导航和生成 client | 复用现有壳、薄路由和交互韧性约束 |
| 后端分层 | 已有 `core/*`、`infra/*`、service-first 和模块化边界 | 继续按最小复杂度升级，不复制历史目录/Mixin |

## 能力决策

| 能力 | 决策 | 当前缺口/引入条件 | Prod 契约 |
| --- | --- | --- | --- |
| IAM 与权限导航 | `reuse-existing` | 只需保持服务端唯一授权、权限键、菜单和路由同步 | [IAM 与权限导航](hanqiang-core-contributions/prod/prod-iam-navigation.md) |
| 配置、密钥、Redis 与分布式锁 | `reuse-existing` | 继续统一配置来源、密钥加载、Redis 用途和锁租约 | [配置、密钥、Redis 与锁](hanqiang-core-contributions/prod/prod-config-secrets-redis-locks.md) |
| 审计、请求关联与可观测性 | `reuse-existing` | 统一 `AuditEvent`、Request ID、结构化日志和异步上下文 | [审计与可观测性](hanqiang-core-contributions/prod/prod-observability-audit.md) |
| Durable 异步投递 | `reuse-existing` | 继续以数据库事实/Outbox 为准，明确任务状态与恢复 | [Durable 异步投递](hanqiang-core-contributions/prod/prod-durable-async.md) |
| 计划任务运行时 | `reuse-existing` | 沿用 `SchedulerJob`/`SchedulerRun`，吸收 pending、基线、租约和告警规则 | [计划任务运行时](hanqiang-core-contributions/prod/prod-scheduler-runtime.md) |
| 前端应用壳与交互韧性 | `reuse-existing` | 沿用分层、薄路由、Tab 隔离、有限懒加载恢复和 shared admission | [前端应用壳](hanqiang-core-contributions/prod/prod-frontend-shell.md) |
| 后端模块分层与依赖边界 | `reuse-existing` | 仅在复杂度达到阈值时新增模块/Adapter/依赖入口 | [后端模块分层](hanqiang-core-contributions/prod/prod-module-boundaries.md) |
| 通用枚举与参考数据 | `candidate` | 有跨域稳定代码/标签且需要受控管理时再建；需租户、唯一约束和缓存版本 | [通用枚举与参考数据](hanqiang-core-contributions/prod/prod-reference-data.md) |
| 文件导入、导出与安全存储 | `candidate` | 有多个消费者或长期批处理需求时再统一批次、存储引用和错误恢复 | [文件导入、导出与安全存储](hanqiang-core-contributions/prod/prod-file-import-export.md) |
| 事件回调与最小 Webhook | `candidate` | 至少一个真实领域事件和一个消费者；需事件幂等、投递审计和 SSRF 策略 | [事件回调与最小 Webhook](hanqiang-core-contributions/prod/prod-event-callback-webhook.md) |
| 文件监控与远程抓取 | `defer` | 需要明确外部文件来源、对象存储、资源授权、Path Traversal/SSRF/ReDoS 方案 | [文件监控与远程抓取](hanqiang-core-contributions/prod/prod-file-monitor.md) |
| 通知 Adapter | `defer` | 需要真实组织渠道、收件人策略、密钥轮换和通知 Outbox | [通知 Adapter](hanqiang-core-contributions/prod/prod-notification-adapters.md) |
| 审批工作流 | `defer` | 需要真实多级/可配置审批消费者；库存纠错只能作为未来首个适配器 | [审批工作流](hanqiang-core-contributions/prod/prod-approval-workflow.md) |
| 服务通信 | `defer` | 需要第二个独立服务、端点身份、跨服务 Trace 和审计 | [服务通信](hanqiang-core-contributions/prod/prod-service-communication.md) |
| 外部集成中心 | `defer` | 需要固定入站/出站契约，且应依赖稳定事件日志和密钥治理 | [外部集成中心](hanqiang-core-contributions/prod/prod-external-integration.md) |

## 分期路线

### 0. 保持并复用现有底座

所有未来任务直接复用 IAM、`AuditEvent`、Request ID、`EmailOutbox`、Celery、`SchedulerJob`/`SchedulerRun` 和现有前后端分层。新增能力不得创建平行权限、平行任务事实、平行 API 类型或跨域全局状态机。

### 1. 按真实需求落地参考数据或文件导入导出

这两项能力可以独立于事件平台启动，但必须先确认至少两个消费者或明确的长期导入需求。首版只做稳定代码/标签或批次导入的最小契约，不复制历史业务字段、FTP 业务目录或页面组件。

### 2. 事件回调内核与最小出站 Webhook

当出现真实领域事件和消费者时，新建独立 Trellis 任务。业务模块只发布事件快照和关联上下文；平台负责提交后登记、投递、租约、重试、死信、审计和受控 HTTP。首版不包含任意 Python 路径、完整 JSONPath 方言、级联事件或复杂编排器。

### 3. 外部集成中心

仅在事件内核稳定且外部契约固定后建设。服务端拥有 schema、字段目录、条件运算符、版本和密钥绑定；前端只编辑结构化配置。入站需认证/幂等键，出站需超时/重试/响应摘要和投递记录。

### 4. 审批流试点

仅在业务确实需要多级或可配置审批时建设，以一个业务适配器验证流程版本、节点实例、待办、动作、超时和审计。库存纠错拥有业务状态和字段，审批内核只消费快照和命令；通知/集成副作用通过事件出口发生。

### 5. 条件触发的暂缓能力

文件监控、通知 Adapter、服务通信分别等待自身事实需求，不提前创建占位 API、配置页面、密钥字段或后台菜单。每项启动门槛、依赖、禁止范围和未来拆分见对应 prod 文档。

## 生产落地共同门槛

任何候选或暂缓能力在进入代码前必须新建独立 Trellis 任务，并提供：

- 领域所有权、数据模型、状态迁移矩阵、数据库约束和租户边界；
- API/事件/任务/前端契约，以及错误响应中的 `detail` 和 `request_id`；
- 服务端权限、敏感数据脱敏、输入校验和威胁模型；
- 幂等键、条件更新/锁、租约、超时、重试、死信和人工恢复；
- 审计事件、结构化日志、Request ID/Trace、指标、告警和容量上限；
- 配置/密钥来源、迁移与兼容窗口、发布、灰度和回滚；
- 单元、集成、API、UI、失败副作用和跨层回归验收。

如果修改后端公开 schema，必须同步生成前端 client；如果变更路由或权限，必须同时验证服务端授权、前端 guards、菜单可见性和重定向。

## 不复制的历史实现

- 不复制另一项目的业务字段、目录、PascalCase 命名、Mixin 形状或 FT/PMS 场景；
- 不允许任意 Python 路径、任意表达式、任意 URL、任意回调函数或前端条件解释器；
- 不把前端按钮可见、Broker 入队、HTTP 2xx 或通知发送当作业务事实成功；
- 不以用户名/前端权限绕过服务端 IAM，不以日志/缓存替代审计和数据库事实；
- 不在没有消费者时提前建设 WeCom、服务通信、文件监控、审批或全量集成管理 UI。

## 文档入口与来源

- [全量能力矩阵](hanqiang-core-contributions/capability-matrix.md)：98 个提交逐文件映射；
- [prod 文档索引](hanqiang-core-contributions/prod/index.md)：15 项归并能力的生产契约；
- [hanqiang 提交总索引](hanqiang-core-contributions.md)：历史分组、主要路径和 Git 复核命令；
- 7 份历史专题/复用指南继续作为证据附录，不替代矩阵和 prod 契约。

后续代码任务必须引用对应矩阵来源和 prod 文档，并在任务自身的 PRD、design、implement 中重新确认当前源码事实；本评估不代表任何候选或暂缓能力已经实现。
