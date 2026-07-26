# 修复定时任务管理审查问题

## Goal

修复 `07-26-scheduled-task-management` 实现审查中确认的 7 项问题，使调度器的环境配置、
启动校验、凭据边界、消息投递、运行分类、并发事务和补发时间输入满足原任务约定，并补齐
能够防止同类回归的自动化验证。

## Background

- 审查范围为 `c8175af` 及其前端生成产物提交 `97eae74`。
- 当前架构保持不变：PostgreSQL 保存定义与运行记录，固定 Beat 每分钟扫描，Celery 默认
  单队列，Worker `--concurrency=1`，所有 Cron 按 `Asia/Shanghai` 解释。
- 本任务是父任务 `07-26-scheduled-task-management` 的修复子任务。只处理已确认 findings，
  不新增调度能力。

## Requirements

### SRF-001 Alert recipient configuration

- `SCHEDULED_TASK_ALERT_RECIPIENTS` 必须能从真实进程环境和 `.env` 读取逗号分隔邮箱。
- 保留邮箱格式校验、大小写不敏感的重复拒绝和空值兼容。
- 测试必须经过 Pydantic Settings 的环境来源，不得只用模型构造参数绕过预解析流程。

### SRF-002 Worker and Beat fail-fast

- `staging`/`production` 缺少 SMTP 或告警收件人时，Celery Worker 与 Beat 必须在启动阶段
  非零退出，不能只记录信号接收器异常后继续运行。
- HTTP API 启动不依赖该校验；`local` 行为保持允许启动。
- 验证必须覆盖真实 Celery 进程的退出码，而不只是直接调用校验函数。

### SRF-003 Credential persistence boundary

- 任务配置模型和提交的 JSON 配置均不得声明或包含密码、令牌、授权信息、访问密钥、连接串
  等凭据。
- 检查必须覆盖嵌套 Pydantic 模型、容器和 union，不能只检查顶层直接 `SecretStr` 字段。
- `credential`、`authorization`、`access_key` 等当前可绕过的常见键必须被拒绝。
- API 返回的定义、运行快照和 Schema 不得使凭据进入 PostgreSQL 或公开响应。

### SRF-004 Bounded Celery dispatch

- 每分钟扫描不得重新投递数据库中全部 `QUEUED` 运行。
- 新建运行仍应尽快投递；broker 发送失败或进程在发送边界崩溃后，持久化运行必须可被后续
  扫描重新投递。
- 技术重投必须按运行限频并限制单次扫描数量，避免长任务或 broker 故障在默认单队列中形成
  每分钟重复消息风暴。
- 保留至少一次语义；极端发送边界允许重复执行消息，由现有运行锁与业务幂等处理。

### SRF-005 Failure classification

- 类路径解析和冻结配置校验失败记为 `CONFIGURATION_INVALID`。
- 已成功构造业务实现后，`run()` 抛出的 `ValueError` 与其他未受控业务异常统一记为
  `EXECUTION_FAILED`。
- `ScheduledTaskSkipped` 的受控跳过语义保持不变；失败类型必须驱动正确的告警类别和限频字段。

### SRF-006 Scan transaction isolation

- 所有活动运行创建路径必须采用一致的数据库并发控制，不能依赖“先查后插”避免竞态。
- 一个任务定义的唯一约束冲突不得回滚同一扫描批次中此前已处理的任务、`next_run_at` 推进或
  已创建运行。
- 并发人工执行与自动扫描仍须保证每个任务最多一个 `QUEUED`/`RUNNING` 运行。

### SRF-007 Shanghai backfill input

- 补发弹窗 `datetime-local` 的最大值必须表示当前上海本地时间，不能使用 UTC 文本冒充本地值。
- 提交值继续按 `+08:00` 转为 UTC；合法的最近上海时间不得被浏览器端错误拦截。
- 不新增日期时间依赖。

### Regression coverage

- 为每项 finding 增加最小、可重复的自动化测试，并运行现有 scheduler、inventory、Celery、
  API、前端类型与迁移回归。
- 测试不得连接真实 SMTP 收件人、非隔离数据库或生产 Redis。

## Acceptance Criteria

- [ ] 真实环境变量和临时 `.env` 中的逗号分隔收件人均能加载；非法邮箱和重复邮箱启动失败。
- [ ] 非本地环境缺配置时 Worker、Beat 的启动命令均非零退出，HTTP API 与 local 不受影响。
- [ ] 顶层、嵌套、容器及 union 中的 Secret 类型和常见凭据键均在持久化前返回 422。
- [ ] 扫描器只领取到期且数量受限的待投递运行；成功投递后不会每分钟重复发送，失败后可重试。
- [ ] 业务 `ValueError` 产生 `EXECUTION_FAILED`，配置解析错误产生 `CONFIGURATION_INVALID`。
- [ ] 并发人工/自动创建最多产生一个活动运行，单个冲突不会丢失同批其他任务的数据库变更。
- [ ] 补发输入的最大值和提交转换都按上海时间工作，并有前端测试覆盖。
- [ ] 新增迁移可升级和降级，测试清理覆盖新增列或索引。
- [ ] 父任务已有 scheduler/API/inventory 测试、后端质量检查和前端构建全部通过。

## Out of Scope

- APScheduler、第二个队列、提高 Worker 并发或修改 Redis/Celery 基础部署结构。
- 通用业务失败重试、批量补发、人工能力开关、恢复邮件或新的告警渠道。
- 调度管理页重设计、动态配置表单、Cron 预览或新增日期组件库。
- 修改库存日报的库存口径、收件人规则或 SMTP 投递语义。

## Notes

- 本任务是跨后端、数据库和前端的修复任务。实施前以 `design.md`、`implement.md` 和
  `e2e-api-tests.md` 作为决策与验证依据。
