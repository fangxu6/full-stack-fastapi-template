# 审批事件回调与并发推进复用指南

> 来源提交：[backend-2026-07-14-fee47911.md](backend-2026-07-14-fee47911.md)
> 关联平台：[事件回调平台](event-callback-platform-2026-01.md)

本文只抽取 `fee47911` 对审批事件回调有影响的可复用规则：并行阶段推进完成后如何生成事件、如何区分人工与超时审批，以及如何避免回调重复或覆盖主流程状态。它不是对通用事件平台所有能力的替代说明。

## 1. 适用问题

人工审批和超时自动审批都可能完成同一并行 AND 组的最后一个节点。如果两条事务各自根据旧快照判断“组已完成”，就会重复创建下一阶段，并重复发送节点分配事件。事件系统看到的症状通常是：

- 同一 `ProcessID` 出现两份相同 `NodeLevel` 的待办；
- 同一审批人收到重复通知；
- `approval_process_completed` 提前或重复触发；
- 回调失败被误认为审批失败，或者回调重试覆盖已提交状态。

事件回调不能单独修复这个问题。必须先让审批状态机返回唯一、已提交的推进结果，再由事件层消费该结果。

## 2. 事件涉及文件与职责

| 文件/符号 | 作用 | 迁移要点 |
| --- | --- | --- |
| `app/services/approve/approval_service.py` | 人工审批，提交后触发节点通过、节点分配和完成事件。 | 事件输入必须来自本次事务的 `created_next`。 |
| `app/services/approve/timeout_service.py` | 超时自动通过，使用 SYSTEM 操作者触发同一组事件。 | 与人工入口共用推进器和事件载荷。 |
| `app/services/approve/process_service.py::advance_process` | 判断 AND/OR/串行规则并返回实际创建节点。 | 不发送事件、不提交事务。 |
| `app/services/approve/approval_event_payloads.py` | 查询流程、节点、角色、用户，组装事件数据和收件人。 | 保持查询+组装纯度，不耦合发送渠道。 |
| `app/services/approve/event_dispatcher.py` | 审批事件码和通用事件平台桥接。 | 发布失败记录 `CallbackStatus=3`，不吞掉主流程事实。 |
| `app/services/event/event_dispatcher.py` | 匹配配置、创建 `Sys_Event_Log`、提交后投递 Celery 首任务。 | 回调顺序、Trace 和去重由平台统一处理。 |

## 3. 事件触发顺序

```text
审批入口（人工或超时）
  -> 锁定 Approve_Process_Master
  -> UPDATE 当前 Process_Detail（ApproveStatus=1 -> 2）
  -> advance_process()
       -> created_next = 实际插入的下一节点集合
       -> ProcessStatus=3 或保持进行中
  -> 提交审批事务
  -> approval_node_approved
  -> 对 created_next 逐条发送 approval_node_assigned
  -> 若 ProcessStatus=3，再发送 approval_process_completed
```

事件发送顺序依赖“先提交、后发布”。这样回调消费者读取数据库时能看到已批准的节点和新分配的节点；即使消息投递失败，也可以从事件日志恢复，而不需要回滚审批事务。

## 4. 事件码与载荷契约

### 4.1 `approval_node_approved`

公共字段建议包括：

```json
{
  "ProcessID": "流程 UUID",
  "ProcessNodeID": "已处理节点 UUID",
  "ApproverID": "审批人 UUID 或 SYSTEM UUID",
  "NodeLevel": "2.1",
  "ProcessCode": "流程编号",
  "BusinessCode": "业务编号",
  "ProcessName": "流程名称",
  "ApproverName": "审批人显示名",
  "ApproveComment": "审批批注",
  "ApproveTime": "YYYY-MM-DD HH:mm:ss",
  "NextNodeName": "下一节点名称，可为空",
  "DetailURL": "发起人流程详情链接",
  "RecipientWXUserIDs": ["企业微信账号"],
  "IsTimeout": false,
  "TimeoutAction": null
}
```

`IsTimeout=true`、`TimeoutAction=AutoApprove` 只由超时自动通过入口增加；不要通过 `ApproverID` 是否为零 UUID 推断自动审批。

### 4.2 `approval_node_assigned`

该事件只为 `created_next` 中真正插入的节点生成。载荷至少包含：

- `ProcessID`、`ProcessNodeID`、`NodeLevel`、`NodeName`；
- `ProcessCode`、`BusinessCode`、`ProcessName`、`InitiatorName`；
- `StartTime`；
- 同时包含 `ApprovalURL`（处理页）和 `DetailURL`（详情页）；
- `RecipientWXUserIDs`：直接分配人优先，否则角色成员，去重并过滤空值。

事件层不能重新读取工作流配置来推测下一节点，否则并行组、部门审批人列表和重提轮次都可能产生错误通知。

### 4.3 `approval_process_completed`

只有 `advance_process()` 没有创建下一节点并把 `ProcessStatus` 设置为 3 时发送。载荷建议包含 `ProcessID`、`BusinessCode`、`WorkflowID`、`EndTime`、`FinalApproverName`、`TotalDuration`、`DetailURL` 和发起人收件人。

## 5. 失败与幂等语义

审批主流程和回调投递是两个事务边界：

1. 审批节点、下一阶段节点和流程终态先提交。
2. 提交后创建/投递事件日志和 Celery 任务。
3. 事件匹配不到配置时返回 `matched=0`，不把流程标记为失败。
4. 事件发布异常时，审批桥接器尝试将 `Approve_Process_Master.CallbackStatus` 更新为 3；这表示“回调失败”，不表示“审批失败”。
5. 首个任务投递失败时保留 `Sys_Event_Log.ExecutionStatus=pending`，由恢复任务补偿。
6. 回调 Worker 必须按 `TraceID + ConfigID + CallbackID` 或等价唯一键幂等执行，避免恢复/重放重复外部副作用。

`trigger_notify_event()` 等纯通知路径不应修改审批主表的 `CallbackStatus`；通知失败应由事件日志、告警和补偿任务承担。

## 6. 并发下的事件保证

要满足“下一阶段只通知一次”，至少需要以下不变量：

- 相同 `ProcessID` 的推进入口按流程主表行锁串行化；
- 当前节点更新带 `ApproveStatus=1` 条件；
- AND 组待办查询使用锁定读，避免旧 REPEATABLE-READ 快照；
- `advance_process()` 返回空 `created_next` 时不得发送节点分配事件；
- 完成事件只由一次状态迁移 `ProcessStatus:2 -> 3` 触发；
- 事件日志创建或回放带唯一去重键；
- 事件消费者可重复执行但业务回写必须幂等。

推荐在数据库中增加唯一约束或等价幂等键，覆盖 `ProcessID + NodeGeneration + NodeLevel + NodeID`；如果业务允许同一节点多次重提，必须把 `NodeGeneration` 纳入键，不能只按 `ProcessID + NodeID` 去重。

## 7. 企业微信通知边界

事件载荷中的 `RecipientWXUserIDs` 来自启用且未删除用户的 `WXUserID`：

- 有直接 `ApproverID` 时优先直接收件人；
- 没有直接分配人时使用角色成员；
- 收件人去重、过滤空字符串；
- 用户禁用或删除后不再加入新事件收件人；
- `ApprovalURL`/`DetailURL` 使用配置的公开基址，不能硬编码开发地址。

事件回调平台只负责传递收件人和链接，不负责绕过权限。通知链接打开后仍需经过前端路由和后端审批权限校验；不要把 Token、Secret 或完整敏感业务快照放进通知模板。

## 8. 跨项目迁移步骤

1. 先定义审批事件码、状态字段和 `NodeGeneration` 契约。
2. 把事件载荷生成器独立出来，只做数据库查询、脱敏和字段组装。
3. 让审批推进器返回实际创建节点，不在事件层猜测工作流下一步。
4. 统一人工与超时入口的锁顺序、提交边界和事件顺序。
5. 事件日志先持久化，消息提交后投递；失败保留 pending 并由恢复任务重试。
6. 为节点通过、节点分配和流程完成建立幂等键，重放保留原始日志和操作者审计。
7. 以企业微信适配器消费 `RecipientWXUserIDs`，不将 WX API 细节写进审批领域服务。
8. 在 MySQL REPEATABLE-READ 下测试人工/人工、人工/超时，并断言事件数量和数据库节点数量一致。

## 9. 验收清单

- [ ] 并行 AND 最后一个节点完成时只创建一份下一阶段节点。
- [ ] 同一推进只产生一个 `approval_node_assigned` 事件链。
- [ ] 节点通过事件先于完成事件，且两者都只在审批提交后发布。
- [ ] 超时自动通过带 `IsTimeout=true` 和 `TimeoutAction=AutoApprove`。
- [ ] 无回调配置不影响审批状态；发布异常只标记回调失败。
- [ ] 消息投递失败可由 pending 日志恢复，不重复执行已完成回调。
- [ ] 事件载荷收件人无空值、重复值和已禁用用户。
- [ ] URL 来自可配置公开基址，通知链接仍受权限保护。
- [ ] 重提/重审场景使用新的 `NodeGeneration`，历史事件可追溯。
- [ ] MySQL 真实隔离级别下人工/人工、人工/超时竞态测试通过。

## 10. CodeGraph 与 Git 复核命令

```bash
rtk codegraph explore "ApprovalService._handle_approval_once ProcessService.advance_process ApprovalTimeoutService.handle_timeouts"
rtk codegraph explore "build_node_assigned_event_payloads enrich_node_approved_event_data enrich_process_completed_event_data"
rtk codegraph node backend/JSECommon/app/services/approve/approval_event_payloads.py
rtk codegraph node backend/JSECommon/app/services/approve/event_dispatcher.py
rtk codegraph node backend/JSECommon/app/services/event/event_dispatcher.py
rtk git -C backend/JSECommon show --stat --summary --format=fuller fee47911
rtk git -C backend/JSECommon show fee47911 -- app/services/approve/approval_service.py app/services/approve/process_service.py app/services/approve/timeout_service.py
```
