# 事件内核跨层 E2E 验证计划

> 无新增 HTTP API。本文件按仓库跨层任务契约记录内部 publish → PostgreSQL → Redis → Worker → AuditEvent 流程；不为测试创建产品路由。表中仍保留完整验收计划，已执行范围见下方记录。

## Environment

- 后端：隔离实例 `http://127.0.0.1:8000`；既有健康检查 `GET /api/v1/utils/health-check/`；前端不适用。
- 数据库：专用 `event_kernel_test` / `event_kernel_pytest`，真实独立会话；migration 使用 `event_kernel_migration_test`。
- Broker：专用 Redis 实例，独立 Worker/必要的事件 Beat，与开发队列隔离，eager=false。
- 测试入口显式装配相同处理器到发布进程与 Worker；生产 include 不可包含此入口。
- 预置人类 Actor A、System Actor、稳定 UUID E；示例信封 event_type=`test.changed`、producer=`test`、schema_version=1、resource_type=`fixture`、resource_id=`case-1`、固定 UTC occurred_at、payload=`{"value":1}`。
- H1/H2 是测试处理器；用隔离持久化副作用计数、同步屏障与不同 Worker 进程验证跨进程行为，不依赖父进程内存计数。
- 故障注入只针对本次测试创建的进程与服务。无永久业务发布者、真实业务 payload 或共享数据库 fixture。

## Cases

| ID / AC | Endpoint / Flow | Setup Data | Request / 操作 | Expected Response / 结果 | Persistence / Side Effects | Failure Assertions |
|---|---|---|---|---|---|---|
| E2E-001 / AC-01,09 | GET health-check；真实 publish→scan→Worker | 迁移完成，A/System/H1 就绪 | 健康检查后事务发布 E 并提交，分钟扫描派发 | HTTP 200；最终 SUCCEEDED，attempt=1 | publication=1、delivery=1、handler 副作用=1，发布/claim/成功审计 | 生产 registry 无 H1；OpenAPI 无 events 路由；Broker 参数只有 delivery ID |
| E2E-002 / AC-02 | publish 事务隔离 | 业务测试写入+E/H1 | 在提交前由第二会话扫描，再回滚；随后另发一个提交事件 | 未提交/回滚事件永不执行；提交事件可执行 | 回滚时业务写入/publication/delivery/审计均无残留 | Broker/handler 计数对回滚事件为 0 |
| E2E-003 / AC-03 | 同 ID 幂等/冲突 | 固定 E、发生时间及 payload | 顺序和两个独立连接并发发布相同内容；再变 payload | 相同内容返回同 publication；不同内容稳定冲突 | 只有一份发布、一组投递、一条发布审计 | 改 request_id/trace_id 不冲突；首次上下文不改；局部冲突不抹除调用方其它写入 |
| E2E-004 / AC-03,04 | 输入、快照与 key 边界 | 原始嵌套 payload | 上限/越界字节与深度、非 JSON/NaN、自引用、未知字段；改变输入副本 | 合法上限通过，越界稳定拒绝；同 key/不同 event_id 是两个事件 | 拒绝前零写入；复制后原始和持久化快照独立 | 不输出验证器原始输入；H1 改自己的嵌套数据不影响 H2 |
| E2E-005 / AC-04,06 | 注册与版本 | H1/H2 明确版本、无匹配事件 | 重复键注册；发布后新增 H2 再重复 publish；Worker 移除/改变 H1 支持版本 | 重复键失败；无匹配只有 publication；已有 delivery 缺失/不兼容 handler 为 FAILED | 不自动生成历史 H2 delivery；缺失/不支持的 handler 副作用为 0 | 未注册/不支持有不同稳定分类，不尝试动态 import |
| E2E-006 / AC-05 | 并发 scanner 与 Broker 故障 | 101 条 due delivery，两个扫描进程 | 并发扫描；一条发送异常；停止 Worker 制造积压 | 单次最多 100；有效派发租约内只一次预占；一条失败不阻断其它条 | attempt 均保持 0；失败条下轮可派发；其它条等待其租约 | 未到期不反复入队；过期发送者释放不能覆写新预占 |
| E2E-007 / AC-05,07 | 派发阶段崩溃 | due delivery | 分别在预占提交后发送前、Broker 接收后确认前终止派发进程 | 租约到期后重新派发并最终完成 | publication/delivery 始终保留；可能重复消息 | 不把 Broker 确认当成功；无永久卡住或提前消耗 attempt |
| E2E-008 / AC-06 | claim 重复/重试等待 | 同 delivery 的重复消息，可控失败 H1 | 并发处理；首次失败后提前再次发送；到期重试至上限 | 一次有效 claim；提前消息 no-op；第 8 次失败 FAILED；第 8 次成功允许 SUCCEEDED | attempt 不超过 8；失败分类、next_* 与终态时间准确 | 无第 9 次调用，无终态复活；重试只来自数据库到期而非双重 autoretry |
| E2E-009 / AC-07 | Worker 丢失与旧结果 | 阻塞 H1、记录 lease token | claim 后终止测试 Worker；另进程恢复；再注入旧 token 成功和失败结果 | 到期恢复 RETRY_WAIT/FAILED；旧/过期结果 no-op | 原始状态转移与审计数量准确 | 即使尚未有新 claim，过期旧结果也不能完成；不以 lease 过期宣称旧副作用停止 |
| E2E-010 / AC-07 | 副作用后崩溃 | 测试用幂等 H1 的持久化唯一副作用 | 副作用已提交、内核结果未写时终止 Worker，恢复后重试 | handler 可被调用两次，幂等副作用仍一份，delivery 最终成功 | 演示消费者幂等与内核 at-least-once 的责任边界 | 不把测试假 handler 的去重能力声称为任意消费者 exactly-once |
| E2E-011 / AC-08 | 审计原子性、Actor 与泄漏 | payload/handler 异常含唯一敏感标记 | 首次处理、重试；注入审计/结果提交故障；连续两条不同 request 的任务 | 首次归 A、自动处理归 System；审计失败使状态回滚并可恢复 | 原始发起人/request 保留；旧结果不追加审计 | 收集 stdout/stderr/结果后端：无 payload、异常标记、SQL 参数；日志无业务标识，无上下文串扰 |
| E2E-012 / AC-04,06 | 多 handler 独立性 | 同 E 的 H1 成功、H2 可重试失败 | 正常处理并重试 H2 | H1 保持成功且不重跑；H2 独立状态 | 一个 publication、两个 delivery、分别审计 | 不因 H2 失败撤销 H1；不依赖消息顺序 |
| E2E-013 / AC-10 | 迁移与应用回滚 | 一次性迁移库；独立有数据应用测试库 | 迁移库 upgrade/downgrade/upgrade；应用库暂停事件派发并回退代码 | 约束/索引/注释完整；应用回滚后新增事实保留 | 两表和 enum 在迁移库按预期变化；应用库记录不丢 | 不对有数据库执行 drop-table downgrade；不删除未处理/失败记录 |
| E2E-014 / AC-01,11 | 无事件注册与既有任务回归 | 生产空注册表、既有 EmailOutbox/Scheduler fixture | 导入应用/Worker/Beat；事件空扫描；运行受影响回归 | 无 SMTP/HTTP 依赖新增；既有任务契约不变 | 无额外业务事件、前端/API 改动 | 事件扫描空闲不制造投递或假事件；测试清理 delivery 在 publication/User 前 |

## Execution Record

已执行的验证不把未实现的完整故障注入矩阵标记为通过：

| Scope | Command / runtime | Result |
|---|---|---|
| Event kernel unit/database/task coverage | `uv run pytest tests/modules/events -q` | 17 passed; isolated `event_kernel_pytest` |
| Existing Celery/EmailOutbox/Scheduler regression | `uv run pytest tests/modules/events tests/core/test_celery.py tests/services/test_email_outbox.py tests/modules/scheduler -q` | 96 passed; isolated PostgreSQL and SMTP test configuration |
| Real broker/worker path | `REDIS_PORT=6381 uv run pytest tests/modules/events/test_runtime.py -q -s` | 1 passed; independent Redis and Celery solo worker; persisted delivery reached `SUCCEEDED` and test handler audit side effect stayed at 1 |
| Migration round trip | `uv run alembic upgrade head`, `downgrade f6a1b2c3d4e5`, `upgrade head` | Passed on isolated `event_kernel_migration_test` |
| HTTP health check | Not applicable | No HTTP entry point was added for the kernel |

## Execution

执行入口、命令、隔离与回滚限制见 [implement.md](implement.md)。未列入 Execution Record 的故障注入、并发和旧 Worker 场景仍是后续补充验证，不因单元测试通过而宣称完成。

每项保存：测试命令、运行模式（eager/真实 Worker）、隔离目标、观察到的状态/审计/副作用和失败日志反向断言。使用可控时钟验证服务边界时间，真实运行时通过短的测试租约、明确同步屏障和有限轮询验证恢复；不得为测试增加生产管理 API。

若环境不可用，先尝试建立/连接计划中的隔离环境，再记录具体阻塞与影响用例；单元通过不能填充 E2E 通过状态。
