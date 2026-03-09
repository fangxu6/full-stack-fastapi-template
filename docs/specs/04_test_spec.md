# Test Spec - Backend 重构补档

## Scope
- 覆盖层次：API 路由、Service 业务编排、CRUD 数据访问、依赖注入链路。
- 重点模块：`users`、`login`、`items`。

## Strategy
- 以“行为兼容”为主线：验证重构前后的外部 API 语义一致。
- 以“分层边界”为辅线：验证 route 不再直接承载业务逻辑，service/crud 各司其职。
- 使用现有测试入口进行回归：`bash ./scripts/test.sh` 或容器内 `scripts/tests-start.sh`。

## Test Cases
- TC1: 用户登录成功路径保持可用，token 相关响应结构不变。
- TC2: 用户创建/查询/更新关键路径保持兼容，常见校验失败仍返回预期状态码。
- TC3: items 业务主流程（创建、查询、权限相关）在 service 层迁移后行为一致。
- TC4: 依赖注入链路可用（DB session、当前用户等依赖在新模块路径下正常工作）。
- TC5: 至少两类失败场景稳定（非法输入、无权限/未认证）。

## Data Setup
- 使用测试数据库与既有 fixture。
- 需要最小化种子数据：普通用户、超级用户、至少一条 item 记录。

## Regression Notes
- 高风险区域：导入路径重定向、依赖注入路径迁移、schema 与 model 映射。
- 若出现回归，优先排查 `api/dependencies/`、`services/` 到 `crud/` 的调用链。
