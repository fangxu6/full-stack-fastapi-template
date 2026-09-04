# 企业微信发送日志的自定义接收人重试

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)
>
> 关联提交：[过期 access_token 受控刷新](backend-2026-06-10-5b65edac.md) · [企业微信通知模块首版](backend-2025-12-02-4d916409.md)

## 1. 提交定位

- 仓库：`backend/JSECommon`
- 完整 SHA：`ff4db2d409309a66dd03cd523fc2f281708947d9`
- 父提交：`5b65edac449b6ecc8e81720c5ed616931e47ce52`
- 作者：`hanqiang <240448317@qq.com>`
- 时间：`2026-06-10 10:36:41 +08:00`
- 原始主题：`feat: support custom wxwork retry recipients`
- 变更规模：5 个文件，新增 225 行、删除 6 行

本提交把人工重试从只能沿用历史接收人扩展为两种显式模式：沿用原接收人，或用管理员提交的一组企业微信 UserID 重试。它只改变失败日志的重试入口和请求契约，不改变自动 Token 刷新、模板渲染或渠道错误分类。

## 2. 变更文件地图

| 文件 | 改动 | 可复用职责 |
| --- | --- | --- |
| `app/api/v1/routes/wxwork/log.py` | 重试路由接收可选 JSON Body，并继续要求 `wxwork:send-log:resend`。 | 将人工重试作为受保护动作，而不是普通日志更新。 |
| `app/schemas/wxwork/log.py` | 新增 `SendLogRetryRequest`，定义模式、UserID 清洗和跨字段校验。 | 在 API 边界统一校验和归一化接收人。 |
| `app/schemas/wxwork/__init__.py` | 导出新 Schema。 | 保持后端/前端契约的唯一导入入口。 |
| `app/services/wxwork/log_service.py` | 根据模式解析原接收人或构造自定义 `RecipientConfig`。 | 将策略决策放在服务层，避免路由和页面重复实现。 |
| `tests/services/test_wxwork_retry_and_question_import_service.py` | 覆盖原模式、自定义模式、空 UserID 和请求模型校验。 | 固化人工重试的安全和审计契约。 |

CodeGraph 显示 `SendLogRetryRequest` 被路由、日志服务、Schema 导出和前端 `SendLogQuery.vue` 共同使用；修改字段时必须同步这些消费者。

## 3. API 与请求契约

```http
POST /api/wxwork/send-logs/{log_id}/retry
Permission: wxwork:send-log:resend
Content-Type: application/json
```

请求体可省略，或使用：

```json
{"retry_mode":"original"}
```

```json
{"retry_mode":"custom_user_ids","custom_user_ids":["zhangsan","lisi"]}
```

字段规则：

- `retry_mode` 只能是 `original` 或 `custom_user_ids`，默认 `original`；
- `custom_user_ids` 为可选字符串数组；每项先 `strip()`，空值过滤，按输入顺序去重；
- `original` 模式会丢弃传入的 `custom_user_ids`，避免请求中隐藏的替代语义；
- `custom_user_ids` 模式至少保留一个有效 UserID，否则 Pydantic 返回校验错误；服务层还保留 400 防线；
- 当前只允许企业微信 UserID，不接受部门 ID、标签 ID 或任意渠道字段。

成功响应为 HTTP 202，形如：

```json
{"message":"重试任务已提交","log_id":"..."}
```

202 只表示重试日志已重置并成功尝试投递 Celery；最终发送结果必须通过 `log_id` 查询。

## 4. CodeGraph 调用链与状态转换

```text
POST /send-logs/{log_id}/retry
  -> require_permission("wxwork:send-log:resend")
  -> WXWorkLogService.retry()
       -> 读取 Sys_WXWork_SendLog
       -> 仅允许 FAILED / PARTIALLY_FAILED
       -> 检查 MaxRetryCount
       -> _resolve_retry_recipient_config()
            ├─ original -> _build_retry_recipient_config()
            │              └─ 部分失败时按 invaliduser/invalidparty 缩小接收人
            └─ custom_user_ids -> RecipientConfig(individuals=[...])
       -> 状态置 PENDING，清理错误和 NextRetryTime
       -> 持久化接收人快照、操作者和更新时间
       -> send_task("wxwork_send_message", [log_id])
       -> 写操作审计，返回 202
  -> worker.process_send_by_log_id()
       -> 重新读取配置/模板/动态数据/接收人
       -> Token、渲染、发送、attempt 明细和最终状态
```

人工重试会把 `RetryCount` 重置为 0，这是该历史实现的已知限制：它适合重新发起一轮人工处理，不适合作为严格的全局尝试计数。新项目应保持历史计数单调，或新增 `RetryGeneration`/新的逻辑发送记录。

## 5. original 模式

`original` 模式不传自定义接收人时：

- 全部失败：沿用日志中的完整 `RecipientConfig`；
- 部分成功：读取 `ErrorDetails.invaliduser`、`invalidparty`，只保留上次被渠道标记为无效且确实存在于原配置中的用户/部门；
- 无法解析错误详情或没有可对应的无效目标：保留原配置，不猜测接收人；
- 解析使用集合去重，输出保持原接收人列表顺序。

这种只重发失败目标的策略依赖企业微信返回的 `invaliduser/invalidparty` 语义。它不是通用失败重试算法：渠道没有逐目标结果时，应回退到人工确认或新的幂等发送记录。

## 6. custom_user_ids 模式

自定义模式会完全替换原 `RecipientConfig`，只构造：

```json
{"individuals":["new-user-1","new-user-2"]}
```

不会继承旧部门、标签或用户。服务在写库前再次检查列表非空，然后才把日志置为 `PENDING`、提交事务并投递任务；校验失败时不会修改日志、提交事务或调用 Celery。

迁移到其它项目时还应在服务端校验：UserID 是否属于当前租户/企业、用户是否存在且启用、操作者是否有跨组织重试权限、单次接收人数上限以及是否允许将消息发送给原审批范围之外的人员。不要只依赖前端选择器。

## 7. 事务、幂等与审计边界

当前服务的顺序是更新日志并 commit，再发布 `wxwork_send_message`。这仍是两个系统之间的非原子边界：commit 成功而 broker 发布失败时，日志可能停在 `PENDING`。当前异常只记录日志，生产实现应增加 outbox/reconciler 或明确的恢复扫描。

建议保留以下事实：

- 原始接收人、人工选择的接收人、操作者、时间和原因；
- 每次实际发送的 attempt、渠道错误码、`msgid` 和最终状态；
- 稳定幂等键，避免客户端超时或重复点击创建多条人工重试；
- 脱敏后的前后数据审计，敏感 UserID 明细需独立权限。

## 8. 测试契约

提交新增的关键场景：

| 场景 | 断言 |
| --- | --- |
| `original` + 忽略自定义列表 | 原 `RecipientConfig` 不变，Celery 只派发一次。 |
| `custom_user_ids` | 空白被过滤、重复被去重，原配置被替换为 individuals。 |
| 构造空自定义列表 | Pydantic `ValueError`，提示至少需要一个有效 UserID。 |
| 服务层收到空列表 | HTTP 400；数据库和 Celery 都不应被调用。 |
| 非失败状态/达到上限 | HTTP 400，不改变日志。 |

还应补充越权租户、禁用用户、超长列表、非法字符、broker 不可用、重复请求和 worker 重投测试。

## 9. 前端协同契约

当前前端类型位于 `frontend/JSE_UI_AI/src/types/wxwork.ts`：

```ts
type SendLogRetryMode = 'original' | 'custom_user_ids'
interface SendLogRetryRequest {
  retry_mode: SendLogRetryMode
  custom_user_ids?: string[] | null
}
```

`src/services/wxwork.ts::retrySendLog(logId, data?)` 集中封装请求；`SendLogQuery.vue` 负责失败/部分失败条件、接收人输入和提交反馈。页面应展示“已受理”，随后按 `log_id` 刷新，而不能把 202 直接显示为发送成功。

## 10. 与企业微信通用模块的组合

该提交依赖既有配置、模板、发送日志和 worker 基础设施：

- `config_service.py` 负责加密 Secret、Token 缓存和过期刷新；
- `send_service.py` 负责模板渲染、URL 兜底、无效接收人分类、Token 失效的一次重试；
- `wxwork_tasks.py` 在独立数据库会话中按 `log_id` 执行，并同步审批操作日志的通知状态；
- `wxwork_notification_service.py` 被审批、培训、APQP、文件监控和 tooling 等业务消费者复用，管理页 DTO 不是唯一入口。

业务模块只应提交稳定的模板编码、动态数据、接收人引用和幂等键，不应直接拼装企业微信 JSON 或读取 Secret。

## 11. 迁移验收清单

- [ ] 重试 API 有独立权限、租户范围和审计；绕过前端直接调用也会被拒绝。
- [ ] 请求模型只接受显式模式；UserID 在后端完成清洗、去重、存在性和启用状态校验。
- [ ] `original` 仅按渠道明确的无效目标收窄；无法解释时不猜测、不静默改收件人。
- [ ] `custom_user_ids` 替换行为、人数上限和跨组织边界有产品定义和自动化测试。
- [ ] 日志状态不会因 broker 发布失败永久停在 PENDING；有 outbox、恢复扫描或人工补偿。
- [ ] 人工重试保留历史 attempt、操作者、原/新接收人和渠道消息 ID，避免覆盖审计证据。
- [ ] 前端 202、超时、部分成功和未知结果均以 `log_id` 查询，不自动重复发送。
- [ ] Secret、Token、动态数据和完整接收人不会出现在普通日志或错误响应。

## 12. CodeGraph 复核路径

| 层次 | 路径/符号 | 结论 |
| --- | --- | --- |
| HTTP 边界 | `app/api/v1/routes/wxwork/log.py::retry_send_log` | Body 可选，权限为 `wxwork:send-log:resend`，状态码 202。 |
| 请求模型 | `app/schemas/wxwork/log.py::SendLogRetryRequest` | 模式联合类型、空白清洗、去重和跨字段校验。 |
| 策略服务 | `app/services/wxwork/log_service.py::_resolve_retry_recipient_config` | original/custom 两条路径。 |
| 重试服务 | `...::WXWorkLogService.retry` | 校验状态/上限、重置日志、提交并派发任务。 |
| worker | `app/tasks/wxwork_tasks.py::send_wxwork_message` | 按 `log_id` 重建发送上下文，失败时回写主日志。 |
| 业务消费者 | `app/services/wxwork/wxwork_notification_service.py` | 审批、培训、APQP、文件监控和 tooling 共用发送服务。 |

## Git 复核

```bash
rtk git -C backend/JSECommon show --stat --summary --format=fuller ff4db2d4
rtk git -C backend/JSECommon show ff4db2d4 -- app/api/v1/routes/wxwork/log.py app/schemas/wxwork/log.py
rtk git -C backend/JSECommon show ff4db2d4 -- app/services/wxwork/log_service.py
rtk git -C backend/JSECommon show ff4db2d4 -- tests/services/test_wxwork_retry_and_question_import_service.py
rtk codegraph explore "retry_send_log SendLogRetryRequest WXWorkLogService.retry _resolve_retry_recipient_config"
```
