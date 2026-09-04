# 企业微信过期 access_token 的受控刷新与重试

> 来源总览：[hanqiang 通用与核心提交整理](../hanqiang-core-contributions.md)
>
> 关联提交：[自定义企业微信接收人重试](backend-2026-06-10-ff4db2d4.md) · [企业微信 Token 刷新分布式锁](backend-2025-12-03-5aaa334e.md)

## 1. 提交定位

- 仓库：`backend/JSECommon`
- 完整 SHA：`5b65edac449b6ecc8e81720c5ed616931e47ce52`
- 父提交：`31d8f3ed5f5d067da896b46cf8e090928f974dd4`
- 作者：`hanqiang <240448317@qq.com>`
- 时间：`2026-06-10 10:14:19 +08:00`
- 原始主题：`fix: retry expired wxwork access tokens`
- 变更规模：3 个文件，新增 40 行、删除 7 行

本提交只处理企业微信返回 access_token 失效这一类发送故障：扩大可识别错误码集合，并在分布式锁竞争时拒绝即将过期的缓存 Token。它没有改变发送日志 Schema、队列协议或人工重试请求；后续 `ff4db2d4` 才增加自定义接收人。

## 2. 变更文件地图

| 文件 | 本提交改动 | 可复用职责 |
| --- | --- | --- |
| `app/services/wxwork/config_service.py` | `refresh_token()` 未获刷新锁时重新读取数据库，并检查 Token 至少剩余 5 分钟；否则返回 HTTP 503。 | 防止并发刷新期间使用 stale Token。 |
| `app/services/wxwork/send_service.py` | 将可受控重试错误码从单个 `40014` 扩展为 `{40001, 40014, 42001}`。 | 将渠道错误分类集中在发送服务。 |
| `tests/services/test_wxwork_retry_and_question_import_service.py` | 参数化三个失效错误码；新增锁竞争且缓存 Token 仅剩 1 分钟时的 503 测试。 | 固化只重试 Token 错误、不能使用 stale Token 的契约。 |

## 3. CodeGraph 调用链

```text
WXWorkSendService.process_send()
  -> WXWorkConfigService.get_valid_token()
       -> Token 缺失或 <= 当前时间 + 5 分钟
       -> WXWorkConfigService.refresh_token()
            -> crud_wxwork_config.get()
            -> redis_lock("wxwork:token:refresh:{config_id}")
            -> 获锁后再次读取并检查安全窗口
            -> decrypt_secret()
            -> WXWorkAPI.get_access_token()
            -> 更新 AccessToken/TokenExpiredTime
  -> WXWorkAPI.send_message()
  -> errcode ∈ {40001, 40014, 42001}
       -> refresh_token()
       -> 原消息最多再发送一次
  -> _classify_send_response()
  -> handle_send_result()
       -> 更新主日志 + 追加 SendLog_Detail
```

`process_send_by_log_id()` 是 Celery 入口：worker 只接收稳定的 `log_id`，重新读取配置、模板、动态数据和接收人快照；Token 刷新和重试不能依赖 API 请求进程中的对象。

## 4. Token 生命周期契约

`WXWorkConfigService._fetch_token()` 调用 `WXWorkAPI.get_access_token(secret)`，使用企业微信返回的 `expires_in` 加上应用本地时间计算 `TokenExpiredTime`。`get_valid_token()` 在没有 Token、没有可解析过期时间，或过期时间不晚于当前时间后 5 分钟时刷新。

刷新使用按配置 ID 划分的锁 `wxwork:token:refresh:{config_id}`。未获锁时先刷新数据库对象、统一时区，再检查安全窗口；只有 Token 仍有超过 5 分钟有效期才返回，否则抛出 `503 Token 刷新中，请稍后重试`。这一步修复了之前“读到 Token 就直接返回”的 stale-token 风险。

发送侧第一次收到 40001、40014 或 42001 后，按配置 ID 强制刷新 Token，并使用同一个消息体再发送一次；刷新异常时保留原始失败响应。非白名单错误码不进入 Token 刷新分支，也不能被通用 HTTP 重试无限重放。

## 5. 错误码与状态语义

| 情况 | 处理 | 最终记录 |
| --- | --- | --- |
| `errcode=0` | 按成功/部分无效接收人分类 | `SUCCESS` 或 `PARTIALLY_FAILED`，保留 `msgid` |
| `40001/40014/42001` 首次出现 | 刷新 Token 后重发一次 | 以第二次响应为准，追加 attempt 明细 |
| Token 刷新失败 | 不再发送，保留第一次渠道响应 | `FAILED`，错误详情脱敏 |
| 其他非 0 错误码 | 不刷新 Token | `FAILED` 或按明确的限流/网络策略待重试 |
| 渠道已接受但响应超时 | 不自动再次发送 | `unknown`/待核验，由查询或人工确认收敛 |

错误码集合是渠道适配器的事实源。迁移到其它项目时应以企业微信官方错误码和实际指标校准，不要把所有 4xxxx 都视为 Token 失效。

## 6. 测试契约

本提交在 `tests/services/test_wxwork_retry_and_question_import_service.py` 中固定两类行为：

```python
@pytest.mark.parametrize("errcode", [40001, 40014, 42001])
async def test_process_send_retries_once_when_wxwork_token_is_invalid(...): ...

async def test_refresh_token_lock_contention_rejects_stale_cached_token(...): ...
```

三种错误码都只触发一次刷新和一次重新发送；锁被占用且缓存 Token 仅剩 1 分钟时返回 503。迁移时还应补充真实 Redis、两个 worker、网络超时、刷新失败、锁 TTL 到期、Token 版本覆盖和渠道已接受但响应丢失测试。

## 7. 跨项目迁移步骤

1. 将渠道调用封装为 `ChannelClient.get_access_token()` 和 `send_message()`，只返回结构化响应。
2. 配置表保存加密 Secret、Token、过期时间、版本/更新时间；建立 `(tenant_id, config_id)` 唯一刷新锁键。
3. Token provider 统一提前刷新窗口（当前 5 分钟）和时区转换。
4. 刷新锁使用 owner token 与原子释放；获锁、未获锁都二次读取。Redis 不可用时显式失败或告警，不能静默伪装成生产安全。
5. 发送 worker 仅对白名单 Token 错误码重试一次，记录第一次和最终响应，禁止递归重试。
6. 发送日志以稳定 ID 重建上下文，每次实际调用追加 attempt；主状态、错误摘要和渠道消息 ID 保持可查询。
7. API 返回 `202` 只表示持久化任务已受理；实际发送状态由日志查询/轮询提供。

## 8. 安全边界与不能照搬的历史行为

- `access_token`、`corpsecret`、HTTP Authorization、动态参数、完整消息体和完整收件人不能写入 INFO/WARN/ERROR；调试日志也应字段级掩码并限制长度。
- Token 刷新锁不能使用全局锁；否则不同企业配置会互相阻塞。
- 固定 30 秒 TTL、同步 Redis 客户端和 `time.sleep()` 只适合低并发兼容层；异步 Web 路径应使用异步锁客户端或把刷新放入同步 worker。
- Redis 未启用时的无锁降级必须显式标记为开发策略；生产环境应拒绝启动或告警。
- 过期 Token 重试不能与通用 HTTP 重试叠加成无限循环；请求超时也不能默认等于未送达。
- 配置/模板禁用、软删除和租户范围应在创建日志、worker 领取、Token 刷新和人工重试时重新校验。

## 9. 当前演进与归因边界

以下能力不是 `5b65edac` 原始提交，但当前代码已具备或由相关提交提供：

| 来源 | 当前能力 |
| --- | --- |
| `5aaa334e` | Redis 分布式锁、owner token、获锁后二次检查和日志脱敏基础。 |
| `ff4db2d4` | 重试 API 支持 `original/custom_user_ids`，并校验自定义 UserID。 |
| 当前 `send_service.py` | 模板卡 URL 兜底、无效用户/部门/标签分类、错误掩码/截断、发送明细和 Celery 入队失败回写。 |
| 当前 `wxwork_tasks.py` | worker 在独立协程/数据库会话中按 `log_id` 发送，并同步审批通知状态。 |

不要把这些后续能力倒归因到本提交；迁移时应按依赖顺序组合，而不是只复制错误码常量。

## 10. CodeGraph 复核路径

| 层次 | 路径/符号 | 结论 |
| --- | --- | --- |
| Token 入口 | `app/services/wxwork/config_service.py::WXWorkConfigService.get_valid_token` | 过期前 5 分钟触发刷新。 |
| 刷新协调 | `...::refresh_token` | 锁竞争后重新读库，stale Token 返回 503。 |
| 渠道客户端 | `app/services/wxwork/wxwork_api.py::WXWorkAPI.get_access_token` | `gettoken` 请求和响应解析；日志必须掩码 Token。 |
| 发送重试 | `app/services/wxwork/send_service.py::WXWorkSendService.process_send` | 白名单错误码只刷新并重发一次。 |
| worker | `...::process_send_by_log_id`、`app/tasks/wxwork_tasks.py::send_wxwork_message` | 以 `log_id` 重建发送上下文。 |
| 结果记录 | `...::handle_send_result` | 主日志与 attempt 明细统一收敛。 |

## Git 复核

```bash
rtk git -C backend/JSECommon show --stat --summary --format=fuller 5b65edac
rtk git -C backend/JSECommon show 5b65edac -- app/services/wxwork/config_service.py
rtk git -C backend/JSECommon show 5b65edac -- app/services/wxwork/send_service.py
rtk git -C backend/JSECommon show 5b65edac -- tests/services/test_wxwork_retry_and_question_import_service.py
rtk codegraph explore "get_valid_token refresh_token get_access_token process_send handle_send_result"
```
