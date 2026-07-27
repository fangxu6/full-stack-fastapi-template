# Technical Design

## Task Map

本任务是父任务，不直接承载运行时代码修改。子任务顺序固定为：

1. `07-27-request-unit-of-work`：HTTP 写事务边界。
2. `07-27-explicit-audit-actor`：审计 actor 与 System Actor。
3. `07-27-safe-celery-observability`：安全 Celery 生命周期日志。
4. `07-27-generic-email-outbox`：通用邮件发件箱与异步投递。

这是实施顺序，不是并行承诺。每个子任务独立规划、实现、验证和归档；父任务负责共享 ADR、交叉依赖和最终集成回归。

## Boundaries

- `backend/app/api/dependencies/database.py` 提供请求级写会话依赖；现有 `SessionDep` 保持读取语义。
- HTTP 路由只声明写会话和 actor 依赖，业务服务负责变更与 `flush/refresh`，不负责事务终结。
- 非 HTTP 入口（Celery、CLI、启动初始化、迁移）显式创建短事务并显式绑定 actor；外部 SMTP 或 broker 调用不放在数据库事务内。
- 审计 actor 以数据库中的 User/System Actor UUID 为唯一来源，Celery 日志上下文不承担审计职责。
- `email_outbox` 是平台邮件投递边界；`inventory_daily_report_delivery` 仍是库存日报的领域边界。
- Celery signal 只清理和绑定 broker task id/name，任务业务状态继续由各模块持久化。

## Cross-Cutting Mechanism Assessment

| 模式 | 项目判断 | 依据 |
| --- | --- | --- |
| HTTP 中间件 | 已适用，保持集中 | 请求 ID、响应日志、异常处理与 CORS 已集中在 `backend/app/main.py` 和 `backend/app/core/exceptions.py`。适合全局 HTTP 行为，不承载业务权限。 |
| FastAPI 依赖注入 | 强烈适用，已是主路径 | `SessionDep`、当前用户和 RBAC 依赖已由 `backend/app/api/dependencies/auth.py` 与 `backend/app/modules/iam/dependencies.py` 提供。认证、权限、actor 和请求级事务继续放在这里。 |
| 上下文管理器 | 强烈适用，已是主路径 | DB Session 已由 `yield` 依赖和 worker 的 `with Session(...)` 管理。事务、锁和外部资源生命周期保持显式。 |
| 装饰器 | 有限适用 | 当前仅启动时数据库可用性重试使用 `@retry`。适合小而纯的技术包装；权限、事务和 HTTP 日志已有依赖注入或中间件边界。 |
| ORM events / signals | 当前不适合扩张 | 项目未使用 SQLAlchemy 事件。库存、调度等业务副作用保留在显式 service/Celery 调用中，避免保存模型时隐式投递消息或改变业务状态。 |
| Celery signals | 仅限安全生命周期日志 | 不用于 Worker/Beat 启动校验或业务副作用；启动配置继续通过 `validate_scheduler_runtime_settings()` 在 `backend/app/core/celery.py` 的应用创建前显式校验。ADR-0010 允许 signal 只绑定 task id/name 并记录开始、成功、失败事件。 |
| 代理/客户端包装 | 暂不需要 | 前端已有 OpenAPI client 与 React Query 的统一错误处理。只有出现多个同类外部服务客户端且重复埋点、鉴权或重试时再增加。 |
| 元类、类装饰器、Monkey patch | 不适合业务层 | 增加隐式行为和调试成本，当前没有需求支撑。 |

## Data Flow

1. HTTP 请求创建会话，依赖解析人类 actor；endpoint 调用服务并 flush；endpoint 成功后依赖提交，异常回滚。
2. 需要邮件的业务事务在同一事务中写入 outbox 行，然后提交；Celery 只接收 outbox ID。
3. worker 在独立事务中领取 outbox 行，事务外执行 SMTP，再以新事务记录成功或安全失败类别。
4. scheduler 的人工创建者继续作为首个投递 actor；无认证调度、重试、租约恢复和补偿流程使用 System Actor。
5. signal 在任务生命周期开始时绑定最小观测上下文，结束后清理；异常只记录任务名、task id 和安全失败类别。

## Persistence

- 新的独立 outbox 表使用 `BIGINT GENERATED ALWAYS AS IDENTITY`、UTC 技术时间戳、显式约束和稳定的邮件领域命名。
- 每个收件人一行，保存 kind、recipient、subject/html 快照或受控链接引用、状态、attempts、next_attempt_at、last_error_category 和审计 actor。
- User 增加唯一 System Actor 标识和必要保护约束；初始化过程幂等创建，禁止通过普通用户 API 暴露或修改。
- 保留原始迁移不可变；新改造只追加 Alembic revision。失败回滚以迁移 downgrade 和应用版本回退为边界，不通过 downgrade 恢复业务数据。

## Compatibility And Risks

- 事务改造会触及用户、IAM、库存和 scheduler 的 HTTP 写路径；先迁移共享依赖，再逐模块移除服务层 commit，避免半套语义。
- 欢迎/恢复邮件改为异步后，HTTP 响应只承诺“已排队”或通用成功消息，不承诺 SMTP 已送达。
- SMTP 接受后 worker 崩溃可能造成重复邮件，这是 ADR 明确接受的至少一次语义；通过 outbox 状态和尝试记录避免静默漏发。
- System Actor 不能成为普通管理员替代品；必须独立于角色权限、登录和用户管理查询。
- 不把 request id、用户 email、actor UUID、任务参数或邮件内容写入 Celery 运行日志。

## Rollback

- 每个迁移先在隔离数据库执行 upgrade/downgrade/re-upgrade。
- 应用回退前保留兼容的 outbox schema 和旧 SMTP 生成器，避免已排队记录无法解释；若不具备兼容窗口，则先停止相关 worker。
- 事务依赖切换按模块提交，任何模块回归失败只回退该模块迁移和代码，不回退已完成的 AI 删除迁移或 scheduler 租约迁移。
