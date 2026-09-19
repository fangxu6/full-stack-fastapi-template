# 2026-09-19 需求复核

## 范围与证据

基线提交 `7091a39`，进入本轮时 git status 干净。审核对象为本任务原 prd/design/implement、历史 Hanqiang 评估和当前源码。所有“问题”均是规划缺口或规范冲突，不表示已有事件代码存在这些 bug。

先读 `docs/llm-wiki/index.md` 与 `sources/scheduler-runtime.md`，再验证当前源码。原任务 PRD 已记录用户确认“内核先行、Webhook/业务适配延期”，本轮不重新要求确认该事实，也不把历史文档的消费者门槛自动恢复为阻塞。

## 问题与修正映射

下表的“原稿”行号指基线提交中的 design.md/implement.md；当前文件已改写，不应把这些旧行号解释为当前行号。

| ID | 严重度 | 原稿问题、证据及后果 | 本版处理与验收 |
|---|---|---|---|
| F-01 | 高 | 原 design:57–70 自动生成 trace_id，却要求同 event_id 的完整信封相同；跨请求重试可能被误判冲突。未定义可选 idempotency_key 是否独立去重、并发冲突是否破坏外层事务。 | R5；规范化业务内容比较，首次上下文保持，event_id 单一去重键，局部冲突隔离；AC-03/04。 |
| F-02 | 高 | 原 design:97–104 只有查询 due IDs 再发 Broker，缺乏持久化派发预占/批上限/发送失败释放，积压会重复排队。现有 `backend/app/modules/scheduler/run_lifecycle.py:97` 与 `backend/app/modules/scheduler/orchestration.py:42` 已提供参考；async-task-guidelines 明确禁止每轮发送所有 queued 行。 | R3；next_dispatch_at、SKIP LOCKED、100 条批次、发送前提交和条件释放；AC-05/07。 |
| F-03 | 高 | 原 design:79 没列 lease_token，但 design:109/121/124 依赖它；缺少状态/字段约束、严格过期结果和 claim 后 handler 缺失的合法边。原 design:126 从 PENDING 失败却写“claim 后”。 | R3；显式 token/状态约束、独立执行租约、修正矩阵；AC-06/07/10。 |
| F-04 | 高 | 原 design:136/142 要把 event/delivery ID 和 handler key 写运行日志；`backend/app/core/observability.py:188` 是封闭接口，logging-guidelines 禁止业务/资源标识。仅“不主动 log payload”也挡不住 `backend/app/core/celery.py:149` 的原始异常链输出。 | R7；业务标识只进入表/受控审计，日志只增加固定事件名；task 边界固定分类并去原始异常链；AC-08。 |
| F-05 | 中 | 原 design:80、109–110 未明确状态/审计同事务，后台 Actor 一律系统化也会丢失人工首发归属。现有 `backend/app/services/email_outbox.py:180`、`:275` 区分首次/重试；`backend/app/core/audit.py:23` 绑定 Actor，`backend/app/modules/audit/service.py:13` 只 add 不 commit。 | R7；首次继承发布者、自动重试/恢复用 System；状态和审计原子提交；AC-02/08。 |
| F-06 | 高 | 原 design:152 把删表 downgrade 当回滚，历史 `docs/hanqiang-core-contributions/prod/prod-event-callback-webhook.md` 明确回滚保留事件/审计。未区分事件保留与 `backend/app/modules/audit/service.py:10` 的 365 天审计清理。 | R8；应用回滚保留数据，downgrade 限一次性隔离测试库；真实业务保留策略留 D-001；AC-10。 |
| F-07 | 高 | 原 design:165 和 implement 前置门槛以“无 HTTP”排除 E2E；workflow.md 要求跨层复杂任务同样有计划。eager 无法证明跨进程注册、Broker 失败或 Worker 丢失恢复。 | R4；新增跨层 E2E 计划，用内部协议与既有健康检查，不造新 API；AC-09。 |
| F-08 | 中 | 原 design:61 只有“大小上限”，无数值、编码/嵌套边界；frozen 信封也未说明嵌套 payload 快照隔离。注册表版本、滚动部署缺失 handler 也不明确。 | R5/R6；64 KiB UTF-8/32 层、严格 JSON、独立快照、精确版本匹配与 Worker 先部署；AC-04。 |
| F-09 | 中 | 原 PRD R2/验收提到租户隔离，design:23 却正确指出无租户模型；`rg tenant_id/workspace_id/organization_id backend/app/models` 无匹配。原 design:148 要“两种状态 enum”，实际仅 delivery 有状态。 | R2；不声称多租户能力；一个状态 enum 加独立错误分类 enum；AC-01/10。 |
| F-10 | 中 | 原 implement 只跑局部 mypy/Ruff，遗漏 ty/format 与全 app gate。现有 `backend/scripts/lint.sh:6` 起定义完整检查；`backend/tests/conftest.py:47` 与 `:74` 要求隔离库并清理数据。模型清理虽在风险中提及，但缺少预期文件。 | R4；补完整检查、独立迁移库和 tests/conftest.py；AC-11。 |

## 本轮决策边界

- 保留原稿既定范围：无真实消费者、无生产假处理器、无 Webhook/UI、有限重试、FAILED 终态、人工重放延期、无匹配保存事件且不历史补投。
- 64 KiB/32 层和 100 条扫描是本版可测试的技术限制，不是业务容量/SLA 承诺。没有新增由本轮擅自决定的业务流程。
- 不把“建内核”扩为通用异步框架；现有领域实现用于约束参考，不统一重构。
- 不证明消费者副作用 exactly-once；lease 只保护结果提交，不能杀掉旧 handler。
- 没有新的产品阻塞问题。未来消费者的保留周期、超时/幂等、历史补投和外部安全契约有明确延期归属，不混入当前 AC。

## 规划检查与限制

需求重新归并为 R1–R8 和 AC-01–AC-11；设计、执行清单、E2E、延期清单与 spec/research manifests 应保持对应关系。最后仍须展示本版摘要并等待新的明确实施批准。

本轮 get_context 报开发者尚未初始化；读取已有 task.json 和任务文件确认任务仍为 planning。该工具状态不是技术设计证据，也不是代码实现已获批准。未执行产品测试、迁移或任何生产运行时操作。

## 本轮文档校验结果

- `task.py validate 09-19-hanqiang-capability-implementation` 通过：implement 8 条、check 10 条真实上下文记录，路径有效。
- 自动上下文注入会截断超过 32 KiB 的 database-guidelines.md 与 async-task-guidelines.md；implement.md 已要求实施/检查者直接读取相关完整章节。
- `git diff --check` 通过；变更仅在当前任务目录，task.json 仍为 planning。本结果不代表产品测试已运行。
