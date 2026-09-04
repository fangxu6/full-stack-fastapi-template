# 服务通信平台复用指南

本指南把 2026-07-28/29 的四个提交整理成可迁移的最小方案：后端提供可靠的 Outbox/Inbox 与业务链路查询，前端提供端点管理、记录处理和链路监控。它描述的是提交中已经验证的边界，不把后续 Tooling 审批或外部集成中心混入通用底座。

## 来源与演进

| 日期 | 仓库 | 提交 | 增量 |
| --- | --- | --- | --- |
| 2026-07-28 | `backend/JSECommon` | `f5b957696d8cbc05b7963e43548eb6860fcc7822` | 通用事件契约、六张事实表、内部入口、Owner 转发和 Worker |
| 2026-07-28 | `frontend/JSE_UI_AI` | `2c33ff61d50090469da4809070cf4e3b66bd590d` | 端点管理、记录列表/详情/载荷/人工动作、路由权限 |
| 2026-07-29 | `backend/JSECommon` | `067238937aff1fd28227d9645ff039b7e6942d5b` | Outbox/Inbox 只读链路聚合、链路索引和状态优先级 |
| 2026-07-29 | `frontend/JSE_UI_AI` | `1a80e1ffd4977f1816d4e011be3f582e660e8b37` | chain/record 双视图、链路展开、筛选分页和竞态修正 |

## 推荐架构

```text
业务事务
  └─ 写本服务 Owner 的 Outbox
       └─ Owner Worker（租约、Attempt、退避）
            └─ POST /internal/service-communication/events
                 └─ 目标写 Inbox，返回 202
                      └─ 目标 Worker 调用业务 handler
                           └─ 可选：目标事务写回执 Outbox

管理浏览器 -> /api/** -> 权限保护的聚合层
                         ├─ 本地 Owner 记录
                         └─ RemoteOwnerRecordClient -> 远端 Owner /internal/**
```

`202` 只代表 Inbox 已持久化；业务处理成功必须以 Inbox 状态和 handler 结果判断。浏览器永远不调用 `/internal/**`，公网 Nginx 对该前缀返回 404。

## 后端迁移清单

### 1. 数据与契约

- 迁移 `Service`、`Outbox`、`Inbox`、`Processing_Round`、`Attempt`、`Audit` 六张表；主键至少包含 `OwnerServiceCode + EventID`，保留 `IsArchived/IsDeleted`。
- 事件信封固定 `service-communication.v1`，包含 EventID、类型/版本、来源/目标、业务键、聚合、关联 ID、发生时间、对象载荷和 PayloadHash。
- 规范化 JSON 使用 UTF-8、`ensure_ascii=false`、递归对象键排序、无空白分隔符；数组顺序不变；摘要计算排除 `payload_hash` 自身。
- `occurred_at` 必须带时区；关联 ID 使用 UUID；payload 必须是对象。

### 2. 服务与内部 API

- `app/services/service_communication/contracts.py`：跨语言 canonical JSON 和 hash 的唯一事实源。
- `app/services/service_communication/service.py`：端点登记/验证/启停、事务内入队/收件、Owner 记录管理和审计。
- `app/services/service_communication/remote_owner.py`：只转发到真实 Owner，不跨库改写；4xx 保留业务错误，网络/5xx 映射为 502。
- `app/services/service_communication/worker.py`：按 Owner 领取、30 秒租约、每轮最多 3 次真实尝试；永久契约错误直接 dead。
- `app/api/v1/routes/service_communication.py`：`/api/**` 管理路由和隐藏的 `/internal/**` 能力/注册/事件/Owner 记录路由。

### 3. 链路查询

`chains.py` 只读合并两张表：有 CorrelationID 用 `correlation:<UUID>`，否则用 `event:<EventID>`。状态按 `dead > paused > processing > delivered > processed > ignored > cancelled` 归并。列表先 SQL 聚合分页，再批量拉取页内记录；详情只返回轻量定位字段。

## 前端迁移清单

- 复制 `src/types/serviceCommunication.ts` 和 `src/services/serviceCommunication.service.ts`，保持响应解包、路径编码和 `statuses[]` 参数序列化。
- 复用 `ServiceEndpointManagement.vue`：服务编码不可变、`expected_version` 防旧页面覆盖、原因必填、基础 URL/CIDR 边界校验。
- 复用 `ServiceCommunicationRecordManagement.vue` 与四个 service-communication 组件：链路默认视图，记录视图用于单事件定位，详情/载荷按需读取。
- 状态标签放在 `recordStatus.ts` 单一事实源；未知状态显示原值，不把异常静默成成功。
- 路由、菜单、按钮同时声明权限；后端权限是最终边界，前端 `disabled` 只是交互提示。
- 若目标项目的 API 客户端没有统一错误包装，保留 `skipBusinessErrorMessage` 等价能力，避免同一错误弹两次。

## 状态与人工操作规则

| 对象 | 状态重点 | 允许操作 |
| --- | --- | --- |
| Outbox | `pending/retry/processing/paused/delivered/dead/cancelled` | 仅 `dead` 可人工新轮次重试；终态可逻辑归档 |
| Inbox | `pending/processing/paused/processed/ignored/dead` | 仅 `dead` 可人工新轮次重试；终态可逻辑归档 |
| Service | `registered/verified/retired` + enabled | 登记后先验证，验证通过才能启用 |

暂停不消耗尚未开始的尝试；人工重试必须填写原因并保留旧轮次、Attempt 和 Audit；归档只隐藏，不删除载荷或事实。

## 复用验收

- [ ] 相同 EventID/Hash 重放幂等；相同 EventID/不同 Hash 返回 409。
- [ ] 202 后业务未完成时，UI 能定位目标 Inbox、轮次和尝试，而不是显示“成功”。
- [ ] 每轮最多三次真实副作用；第三次失败进入 dead，永久契约错误不盲目重试。
- [ ] Owner、方向、EventID 三元组始终用于详情和人工操作；远端记录通过内部受限转发。
- [ ] 链路死信不会被 Outbox delivered 掩盖；无 CorrelationID 时能回退到 event 链路。
- [ ] 归档默认隐藏但可恢复；完整载荷读取产生 `payload_view` 审计且不出现在列表摘要。
- [ ] `/internal/**` 不进 OpenAPI、不接受用户 JWT、公网和前端代理均返回 404。
- [ ] 前端测试覆盖权限禁用、空状态、链路展开、数组筛选、旧响应竞态和动作确认。

## 复核命令

```bash
git -C backend/JSECommon show --stat --oneline f5b95769
git -C backend/JSECommon show --stat --oneline 06723893
git -C frontend/JSE_UI_AI show --stat --oneline 2c33ff61
git -C frontend/JSE_UI_AI show --stat --oneline 1a80e1ff
rtk codegraph explore "canonical_event_document payload_hash_hex verify_payload_hash ServiceCommunicationEventEnvelope"
rtk codegraph explore "ServiceCommunicationService receive_event enqueue_outbox_event RemoteOwnerRecordClient"
rtk codegraph explore "ServiceCommunicationChainService list_chains get_chain_detail"
rtk codegraph explore "ServiceCommunicationRecordManagement ServiceCommunicationChainListTable ServiceCommunicationRecordDetailDrawer"
```

更详细的运行与接入说明见 [`docs/service-communication-integration.md`](service-communication-integration.md)；本文件重点是跨项目拆分、依赖顺序和验收边界。
