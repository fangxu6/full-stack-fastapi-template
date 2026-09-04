# 通用定时任务平台复用指南

> 整合提交：后端 `012d8658`、`0350dc41`、`c978b4b6`、`a3b3ddff`、`14910a94`、`2cebb894`；前端 `2c373c2c`、`8978bbe5`。
>
> 目标：在其它项目中复用“可配置 Cron + 异步执行 + 通知投递 + 执行审计”的平台骨架，再按领域接入 PMS、报表、设备、Tooling 等任务适配器。

## 1. 最小架构

```text
管理 UI
  -> Task API / Execution API
  -> TaskService（校验、审计、事务）
  -> Task/Delivery/DomainConfig 表
  -> BeatScheduler（DB -> PeriodicTask）
  -> dispatch_task（创建/领取执行槽）
  -> execute_<task_type>（领域适配器）
  -> DeliveryAdapter（email/webhook/消息）
  -> Execution Master + Detail + Message History
```

四个稳定接口足够支撑多数项目：

```python
create_task(payload) -> task_id
claim_execution(task_id, trigger_source) -> execution_id | active_execution
execute(execution_id) -> ExecutionResult
retry(execution_id) -> new_execution_id
```

路由不直接访问 Celery、Beat 表或领域 SQL；Worker 不依赖 HTTP 请求上下文。

## 2. 任务与执行数据模型

### 任务定义

主表至少包含：

`id`、`task_type`、`name`、`cron`、`timezone`、`effective_at`、`expires_at`、`enabled`、`deleted`、创建/更新审计字段。

投递配置单独存储：`delivery_method`、模板/收件人/连接配置引用、用户变量 JSON。领域配置按 task_type 拆表或 JSON，但必须可版本化。

### 执行日志

主记录保存任务快照（类型、名称、投递方式）、`trigger_source`（cron/manual/retry）、`trace_id`、消息 ID、状态、排队/开始/结束时间、耗时、明细计数、摘要和错误。明细保存 `detail_type`、`detail_key`、顺序、状态、摘要和错误。

建议状态：

```text
pending -> executing -> success
                    \-> failed -> retry(pending)
pending -> timeout
```

状态更新需带当前状态条件或版本号，防止 Worker、恢复任务和人工重试互相覆盖。

## 3. Beat 与 Celery

### Beat 同步

全量同步只发布满足以下条件的任务：

```sql
deleted = 0
AND enabled = 1
AND effective_at <= now
AND expires_at > now
```

用稳定前缀（如 `scheduled_task_<id>`）作为 `PeriodicTask.name`，同名更新、不存在创建；不在活动集合的旧任务设为 disabled。Cron 解析必须校验 5/6 段、时区和最小执行间隔，不能仅依赖前端。

#### Beat 运行基线（`a3b3ddff`）

动态同步 Beat 配置时，`PeriodicTask.last_run_at` 是调度器运行事实，不是普通配置字段，必须采用“新建初始化、已有值保留”的规则：

```python
if periodic_task is None:
    periodic_task = PeriodicTask(..., last_run_at=now)
else:
    # 只修复历史空值，不覆盖 Beat 已记录的上次运行时间
    if periodic_task.last_run_at is None:
        periodic_task.last_run_at = now
```

不要在每次全量同步、服务启动、午夜重载或任务编辑时把 `last_run_at` 写成当前时间。覆盖运行基线会改变 Celery Beat 的 `is_due()` 判断，可能跳过应执行的 Cron，也可能让重载后的任务立即补发。详细提交证据见 [a3b3ddff 提交说明](backend-2026-07-15-a3b3ddff.md)。

Beat 同步器还应遵守：

- `PeriodicTask.name` 使用稳定任务 ID；任务改名不产生新 Beat 记录；
- `last_run_at` 与业务执行日志、Celery task id、业务 trace_id 分开保存；
- 过期/禁用任务只关闭 Beat 记录，不删除，以保留历史关联；
- 同步器在单个事务中提交，失败回滚并释放独立 Engine/Session；
- 在目标 Celery 版本和时区下验证 naive/aware datetime 与 `schedule.is_due()` 的实际语义。

### 派发与执行槽

Beat 只投递 `dispatch_task`。派发器负责：

1. 再次检查任务启用和有效期；
2. 原子领取一个 pending 执行槽；已有 pending/executing 时返回 skip/conflict；
3. 提交执行记录后再发送 `execute_task`；
4. 发送失败把 pending 标记 failed，并保留错误。

Worker 开始时把状态改为 executing；无论业务异常、软超时还是进程崩溃，都要由兜底任务把陈旧 pending/executing 标成 timeout/failed。

`send_task` 后是否回填 Celery task id 要谨慎：业务 `trace_id` 应在第一次创建时固定，不能被后续重试的 Celery id 覆盖。

#### 派发成功的状态语义（`14910a94`）

手动执行和重试在领取执行槽后先提交 `Status=pending`，再调用统一的 `dispatch_scheduled_task`。`send_task()` 成功只证明消息已交给 Broker，API 仍返回 `pending`；具体 Worker 开始后才改为 `executing`，完成后才进入 `success`、`failed` 或 `timeout`。

```text
claim_pending_execution -> commit(pending)
  -> send_task(task_id, trigger_source, execution_id)
       ├─ 成功：返回 execution_id + pending
       └─ 异常：pending -> failed，保存错误/结束时间/耗时
```

该边界必须与前端文案、监控和重试按钮一致：不要把“已入队”显示为“执行成功”。`run_task()` 与 `retry_execution()` 应继续使用活动执行槽约束（`pending`/`executing`），必要时增加请求幂等键，防止 Broker 响应丢失时客户端重试创建重复执行。

## 4. 领域适配器

统一采用：

```text
collect(scope, filters) -> matched_items, skipped_items, counters
build_details(matched, skipped) -> execution_detail rows
build_variables(matched, counters) -> runtime variables
deliver(runtime variables) -> message_id
```

PMS 适配器的可复用规则：

- `all_devices` 与 `specified_devices` 必须是两个明确模式；空设备数组不能同时表示“全部设备”和“未选择”。
- 设备查询过滤未删除、启用状态；指定设备不存在/停用时写 skipped，而不是静默丢弃。
- 计划查询限制状态和截止日期，结果稳定排序。
- 逾期/即将到期计数从同一 matched 集合计算，避免摘要与明细不一致。

### Tooling 预警适配器（`2cebb894`）

Tooling 预警应把“可选对象查询”和“执行候选扫描”分开，使用受控的预警类型映射：

| `warning_type` | 允许的 Tooling 类型 | 必填阈值 |
| --- | --- | --- |
| `socket_life` | `Socket` | `life_warning_percent_red` |
| `sample_tube_expiry` | `SampleTube` | `sample_tube_advance_remind_days` |
| `sample_tube_bin1_safety_stock` | `SampleTube` | 按既有样管规则 |

- Socket 寿命只用一个红阈值：`remaining_life / total_life * 100 <= red` 才进入 `matched_items`，输出统一 `warning_level="warning"`。黄色阈值可作为历史兼容字段保留，但新建不要求、执行不读取，不能让前端字段决定后端匹配。
- 新增轻量选项接口 `GET /api/scheduled-tasks/tooling-options`，参数为必填 `warning_type`、`page/page_size`（默认 50、上限 200）、可选 `keyword` 和逗号分隔的 `tooling_ids`。关键字匹配编码/名称/组别；已选 ID 与关键字使用 OR，ID 去重并校验 UUID；按编码升序返回 `{items, total, page, page_size}`。
- `warning_type` 到 Tooling 类型的映射必须由服务层维护；未知类型、组别类型不匹配、指定对象不存在或类型不匹配都在服务层拒绝，不能只依赖表单选项。
- `all_toolings` 扫描在数据库阶段按类型、`Status=Active`、未删除、组别和红阈值预过滤；总寿命缺失/无效或剩余寿命缺失的对象仍保留为候选，随后写入 skipped 明细，不能为提速丢失审计事实。`specified_toolings` 则按 ID 读取并报告缺失对象。
- 为候选扫描和组别选项建立组合索引：`Tooling(ToolingType, Status, IsDeleted, GroupCode, ToolingCode)`、`Tooling_Group(IsDeleted, ToolingType, GroupCode)`。迁移应先检查索引再创建，并提供对称的安全降级。

前端可以把 `warning_level="warning"` 映射为自己的文案或颜色；不要把 5%/10% 展示常量反向当成执行规则。

## 5. 模板和通知

系统变量与用户变量分离：

```json
{
  "company_name": "JSE",
  "batch_label": "B-01"
}
```

系统变量通过注册表生成，如 `NOW_YYYY`、`NOW_MM`、`NOW_DD`、`NOW_YYYYMMDDHHMMSS`、`mtplan`、统计计数。`mtplan` 这类表格变量可同时提供 text/html；其它变量默认 HTML 转义并限制长度。

通知适配器必须：

- 校验连接配置、模板和收件人启用状态；
- 在写发送历史前把运行时对象序列化为 JSON，读取时可恢复特殊类型；
- commit 失败先 rollback；
- 明确发送“已提交”与“已发送”的状态，不把队列成功当成 SMTP 成功；
- 对非幂等邮件/HTTP 投递提供业务幂等键，避免重试重复发送。

## 6. API 和权限

最小 API：

```text
GET    /scheduled-tasks/tasks
GET    /scheduled-tasks/tooling-options
POST   /scheduled-tasks/tasks/{type}
GET    /scheduled-tasks/tasks/{id}
PUT    /scheduled-tasks/tasks/{id}
PATCH  /scheduled-tasks/tasks/{id}/enabled
DELETE /scheduled-tasks/tasks/{id}
POST   /scheduled-tasks/tasks/{id}/run
GET    /scheduled-tasks/executions
GET    /scheduled-tasks/executions/{id}
POST   /scheduled-tasks/executions/{id}/retry
```

权限至少拆分：列表、详情、创建、更新、启停、删除、手动执行、日志列表、日志详情、重试。前端按钮权限只是体验控制，后端必须再次校验。

## 7. 前端复用分层

1. `types`：以联合类型表达 task_type、状态、scope 和响应结构。
2. `services`：统一解包 API 响应；写请求显式关闭网络自动重试。
3. 纯组件：表单、设备/对象选择器、模板变量编辑器、执行详情抽屉通过 props/v-model 工作。
4. 领域页面：任务管理负责动作编排，日志页负责筛选/分页/Trace，抽屉只读展示。
5. 路由 query：用 `task_id`/`trace_id` 支持深链；读取 query 时处理字符串、数组和空值。

执行抽屉应支持可选 `detailData`：已有缓存或示例数据时直接渲染，否则才请求详情，避免重复网络调用。

## 8. 可靠性与安全边界

- Beat 同步失败不能只写 warning；使用 outbox、补偿扫描或启动自愈确保最终一致。
- 任务执行槽使用数据库唯一约束/行锁/条件更新，避免并发 Cron 与手动执行重复。
- 重试只允许明确可重试状态；SMTP 认证失败、参数非法等错误应快速失败。
- 错误、摘要和模板变量脱敏，禁止保存密码、Token、完整请求体。
- JSON 变量大小、Trace 长度、明细数量、执行时长和邮件附件大小设上限。
- 多租户项目在任务、执行、投递配置和 Beat 查询中都带 tenant_id，不能仅靠 UI 过滤。
- Cron 与时区统一存储；夏令时切换、服务器时区变化和时间边界写测试。

## 9. 迁移顺序

1. 迁移任务/投递/领域配置/执行主表/明细表及索引；Tooling 预警项目同时迁移候选组合索引。
2. 接入 TaskService、ExecutionService、BeatScheduler 和一个领域适配器。
3. 注册 Celery 任务与专用队列，先跑手动执行，再启用 Beat。
4. 接入模板/通知历史、权限和操作日志。
5. 增加重试、Trace 聚合、陈旧执行恢复和 outbox 补偿。
6. 最后复制前端页面和组件；前端类型必须与后端契约先对齐。

## 10. 验收清单

- [ ] 任务创建、更新、启停、删除后 Beat 配置幂等正确。
- [ ] Cron/manual/retry 三种触发均有可追踪执行记录，队列派发成功先保持 `pending`。
- [ ] 并发执行只允许一个活动槽；陈旧记录可恢复为 timeout。
- [ ] Worker 成功、失败、软超时、进程重启均能回填主/明细状态。
- [ ] 明细计数、摘要计数、通知历史和 MessageID 可相互关联。
- [ ] 模板 text/html、变量转义、序列化/还原和时区占位符有测试。
- [ ] 写请求无网络自动重试；重试有幂等键或人工确认。
- [ ] 权限、租户隔离、敏感字段脱敏和审计日志通过安全检查。
- [ ] 迁移脚本可重复执行，旧数据范围语义有明确校正策略。
- [ ] Tooling 预警类型映射、选项接口权限、分页上限和无效 UUID 校验正确。
- [ ] Socket 预警只由红阈值触发，黄色历史字段不会改变匹配；寿命异常对象仍生成 skipped 明细。
- [ ] Tooling 候选和组别组合索引已迁移且重复执行不会报错，执行查询计划未退化为全表扫描。

## 11. 提交与当前工作树边界

`012d8658` 是后端骨架；`0350dc41` 增加范围、模板、Trace、重试和邮件事务；`c978b4b6` 修复异步 ORM 完整回读；`a3b3ddff` 固化 Beat 的 `last_run_at` 基线；`14910a94` 明确队列派发成功仍为 `pending`；`2cebb894` 简化 Socket 预警并增加 Tooling 候选接口/索引；`2c373c2c` 是前端首版；`8978bbe5` 完善交互和测试。当前工作树还有更晚的 tooling、B2B_SGM、报表校验能力，复用时应按后续提交单独评估。

`2cebb894` 只修改后端；前端 `useToolingManagementPage.ts` 中的黄色/红色展示阈值不属于该提交，迁移时需单独决定是否同步 UI 文案和类型。

## 12. 复核命令

```bash
rtk git -C backend/JSECommon show --format=fuller --stat 012d8658 0350dc41 c978b4b6
rtk git -C backend/JSECommon show --format=fuller --stat a3b3ddff 14910a94
rtk git -C backend/JSECommon show --format=fuller --stat 2cebb894
rtk git -C frontend/JSE_UI_AI show --format=fuller --stat 2c373c2c 8978bbe5
rtk codegraph explore "ScheduledTaskService.list_tooling_options _validate_tooling_payload ToolingTaskQueryService.collect_warning_items" --max-files 40
rtk codegraph explore "ScheduledTaskService BeatSchedulerService dispatch_scheduled_task execute_pms_task" --max-files 40
rtk codegraph explore "TaskManagement ExecutionLogManagement ScheduledTaskFormDialog ExecutionLogDrawer" --max-files 40
```
