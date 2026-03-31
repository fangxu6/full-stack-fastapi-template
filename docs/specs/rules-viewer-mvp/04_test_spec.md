# Test Spec

## Scope
- Covered layers: backend API, frontend integration surface, generated client contract, UI build correctness.

## Strategy
- AC1/AC2 通过后端 API 测试与前端页面集成行为共同覆盖。
- AC3/AC4 由后端 API 测试直接验证白名单与空目录行为。
- AC5 通过前端构建、路由接入和状态分支实现验证。

## Test Cases
- TC1: 已登录用户访问规则列表接口时，返回 `docs/rules/*.md` 摘要与正确 `count`。
- TC2: 已登录用户读取合法 slug 时，返回标题、相对路径和正文。
- TC3: 读取不存在 slug 时返回 `404 Rule document not found`。
- TC4: 未登录访问 rules 接口时返回认证错误。
- TC5: 前端 `/rules` 页面能编译通过，并通过生成 client 获取列表和详情。
- TC6: 当列表为空时，前端显示空态而不是崩溃。
- TC7: symlinked `.md` 文件不会进入规则列表，访问其 slug 时返回 `404`。

## Data Setup
- 使用仓库当前 `docs/rules/*.md` 作为测试数据源。
- API 测试复用现有登录夹具获取 superuser token。
- 不需要额外数据库记录。
- symlink 安全测试使用仓库内临时目录；若当前环境不支持创建 symlink，则测试跳过。

## Regression Notes
- API router 新增 `docs` tag，需关注 OpenAPI client 生成结果。
- 侧边栏新增入口，需确认不会影响现有 Dashboard / Items / Admin 导航。
- route tree 会在前端 build 过程中重生成，需确认新页面被正确纳入。
