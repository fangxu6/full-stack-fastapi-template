# Implementation Plan

1. 在 P0 已合并的基础上盘点所有 AuditFields 模型、HTTP 写入口和非 HTTP writer。
2. 添加 User 的 System Actor 标记、partial unique index 和幂等初始化；覆盖启动重复执行。
3. 实现 Session actor bind helper 与 ORM hook；对 insert、update、creator 篡改和缺 actor 建立最小测试。
4. 将 HTTP 写 actor 绑定到 `WriteSessionDep`，删除业务服务的手动 AuditFields 赋值。
5. 迁移 scheduler、worker、CLI、bootstrap 的 actor 解析；确认手工发起 actor 跨异步路径保留。
6. 保护 System Actor 的认证、用户列表/详情、更新/删除和角色分配；运行迁移往返与回归测试。

## Validation

- `python -m pytest backend/tests/models backend/tests/api backend/tests/modules`
- 迁移隔离数据库：重复初始化后 System Actor 数量为 1，unique index 生效。
- 对每个 AuditFields 模型测试缺 actor 失败、创建字段一致、更新字段变更、creator 不可修改。
- 检查所有 worker/CLI/任务 Session 在写入前绑定 actor，且日志不含 actor UUID/email。

## Review Gate

审核 System Actor 的不可登录/不可管理边界、所有非 HTTP writer 清单及 P0 的 WriteSessionDep 集成后，才可 `task.py start`。
