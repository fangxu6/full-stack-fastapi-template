# 引入 Celery 与 Redis

## Goal

为后端提供可部署、可验证的异步任务运行时，并交付首个受限业务任务：每日库存
邮件日报；不在本任务实现告警规则、outbox、Webhook 或用户通知渠道。

## Confirmed Facts

- 现有后端是 FastAPI + SQLModel/PostgreSQL，生产镜像以四个 Uvicorn worker
  运行；仓库尚无 Celery、Redis、后台 worker 或调度器。
- `backend/pyproject.toml` 未声明 Celery 或 Redis 客户端依赖；`compose.yml` 和
  `compose.override.yml` 均未定义 Redis、Celery worker 或 Beat 服务。
- 已批准的告警设计选择 Celery + Redis 作为未来执行层，PostgreSQL outbox 为
  业务事实来源；当前没有获批的告警事件、阈值、渠道、收件人或 outbox 表。
- 后台任务只可接收可序列化值，任务内必须创建数据库 session 并重载记录；不得
  传递 ORM 对象、凭据或任意业务载荷。
- 用户现在明确要求优先引入 Celery 与配套 Redis，覆盖先前“等待首个业务场景”
  的延后决定。
- 首期同时部署 Celery worker 与 Beat；Beat 在 `Asia/Shanghai` 每日 08:00 创建
  前一自然日的库存邮件日报，并每 15 分钟扫描可重试投递。
- Redis 采用 AOF 持久化、命名卷、密码认证和仅内部 Docker 网络的默认策略；不
  映射宿主机端口。
- 保留私有 `runtime.ping` 诊断任务：仅接收受长度限制的字符串并返回原值，不
  提供 HTTP 入口、不访问数据库、不注册 Beat、也不承载业务工作。
- 启用 Redis 结果后端，仅用于 `runtime.ping` 和未来明确需要返回值的技术任务，
  并设置短结果过期时间。未来告警投递必须忽略 Celery 结果，以 PostgreSQL
  outbox 状态为准。
- 采用 `task_acks_late=True` 的至少一次投递语义；worker 在执行中意外终止时
  允许 broker 重新投递。未来业务任务必须在其持久化边界实现幂等，不能假设
  Celery 提供恰好一次执行。
- Worker 固定使用 `--concurrency=1`，避免在没有已知任务负载时按 CPU 核数创建
  未经评估的子进程；未来扩容需由具体任务的吞吐与隔离需求驱动。
- 不设置 Celery 全局自动重试；`runtime.ping` 不重试，未来业务任务必须显式
  声明可重试异常、最大次数和退避策略。
- 首期仅使用 Celery 默认单队列；不预建告警或其他命名队列。未来任务隔离由
  具体任务的吞吐、故障隔离和优先级需求驱动。
- Redis broker 可见性超时固定为 `CELERY_VISIBILITY_TIMEOUT_SECONDS=3600`；
  `runtime.ping` 结果使用 `CELERY_RESULT_EXPIRES_SECONDS=900` 自动过期。未来
  超过一小时的任务必须拆分或在其任务设计中重新评估队列语义。
- 库存日报面向所有启用的加工单位，按 `business_date <= 报表日期` 固化原料与成品
  的非零库存 JSON 快照；即使库存为空也创建日报。
- `INVENTORY_DAILY_REPORT_RECIPIENTS` 是“加工单位 UUID -> 邮箱列表”的 JSON 映射。
  首次成功解析后固化逐邮箱投递目标；缺少映射时保留失败日报，后续重试可重新解析。
- 日报仅在每日 08:00 至 08:15（上海时间）内创建，错过窗口不补发。单邮箱总尝试
  最多 8 次，成功或终止状态均可由数据库记录和 Celery 日志追踪。

## Requirements

- 增加受版本约束的 Celery 与 Redis Python 依赖及类型安全的集中配置。
- 在生产与本地 Compose 形态中运行 Redis、Celery worker 和 Beat。
- 任务运行时不改变现有 HTTP API、请求错误协议或前端；库存日报使用独立的
  `inventory_` 持久化记录，不伪造用户审计人。
- 提供最小、可重复执行的验证路径，证明任务被 worker 消费，且 Redis 不被用于
  持久业务事实。
- 保持未来告警设计的边界：具体业务事件仍需独立任务并使用 PostgreSQL outbox。
- 仅使用现有 SMTP 能力投递库存日报，不增加 API、前端、站内通知、告警适配器或
  命名队列。

## Initial Scope Boundary

- 不实现告警事件、通知适配器、Webhook、邮件兜底、outbox 表、规则管理或站内
  通知。
- 不把 Redis 用作缓存、会话、分布式锁、数据库替代品或业务事件存储。
- 不添加新的公开 API；若需要运行时探针，优先使用 Compose/worker 验证而不是
  暴露管理端点。

## Acceptance Criteria

- [ ] 依赖锁定、配置校验和 Compose 服务能在生产及本地开发形态一致启动。
- [ ] Worker 能消费一个明确界定的最小验证任务；任务不接收 ORM 对象或敏感值。
- [ ] Redis 使用认证、持久化和网络暴露策略得到明确说明。
- [ ] Redis 结果后端只保存短期技术任务结果，未来告警投递不依赖它。
- [ ] Worker 中断后允许任务重投；设计明确未来业务任务的幂等责任。
- [ ] Compose worker 固定以单并发运行，未来扩容不改变首期行为。
- [ ] 全局运行时不隐式重试；具体业务任务拥有其重试决策。
- [ ] 首期只有默认单队列，不预建未被消费的业务队列。
- [ ] broker 可见性超时为 3,600 秒，技术结果为 900 秒，且未来长任务必须重新
  评估该上限。
- [ ] 后端、worker 与 Beat 的启动、停止、健康检查和失败行为不影响既有 API。
- [ ] 测试覆盖 eager 单元路径与至少一个隔离的 worker/broker 集成路径。
- [ ] 没有引入未获批准的告警、outbox 或用户通知功能。
- [ ] 每日 08:00 上海时间为全部启用加工单位创建前一日库存快照；08:15 后不补发。
- [ ] 原料与成品的非零库存分别呈现，空库存照常生成并投递日报。
- [ ] 每个邮箱独立追踪投递、最多八次尝试，缺少收件人或 SMTP 失败可按 15 分钟
  间隔重试，且已成功邮箱不重复发送。

## Deferred Work

See [deferred iterations](./deferred-iterations.md) for the scope register.

- 具体告警事件、PostgreSQL outbox、Webhook 渠道适配器、升级策略和任务路由仍由
  后续业务任务拥有；本任务不创建它们。
- 告警队列或其他命名队列、提高并发、结果长期保留、任务优先级和任务级时间
  限制都需要真实负载或业务需求后单独评审。
