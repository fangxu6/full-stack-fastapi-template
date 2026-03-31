# Requirement Spec

## Background
- 当前仓库已经把 `docs/rules/*.md` 作为工程规则来源之一，但这些规则只能在代码仓库里离线查看，不利于登录后的后台用户直接查阅，也不利于后续把 `docs/` 内容逐步做成统一的在线文档入口。

## Goals
- 提供一个登录后可访问的 rules 在线查看 MVP。
- 用户可以浏览 `docs/rules/*.md` 列表并查看单篇正文。
- 保持实现简单，但为后续扩展到 `docs/specs/**` 或更多 `docs/**` 内容预留结构。

## Scope
- In scope:
  - 只读浏览 `docs/rules/*.md`。
  - 后端提供规则列表和单篇内容接口。
  - 前端提供一个受保护的 `/rules` 页面与侧边栏入口。
  - 正文先按纯文本展示，不做 Markdown 富渲染。
- Out of scope:
  - 编辑、删除、上传规则文档。
  - 全文搜索、目录树、标签过滤。
  - `docs/rules/` 子目录递归读取。
  - `docs/specs/**` 或其他 `docs/**` 内容展示。
  - 匿名访问和更细粒度权限控制。

## Acceptance Criteria
- AC1: 已登录用户访问 `/rules` 时可以看到 `docs/rules/*.md` 列表。
- AC2: 用户选择某篇规则后，可以看到标题、来源路径和正文原文。
- AC3: 当 `docs/rules/` 为空时，页面有明确空态，不返回 500。
- AC4: 非法 slug 或白名单外路径无法被读取，接口返回明确错误。
- AC5: 页面包含加载态和错误态，前端不会因为单篇读取失败而崩溃。

## Constraints
- 只允许访问仓库内 `docs/rules/*.md`，禁止任意路径读取和路径穿越。
- 保持与当前仓库架构一致：`FastAPI + OpenAPI + generated client + TanStack Query + TanStack Router`。
- 不手写独立请求层；前端必须通过生成式 client 调用后端接口。
- 不手动编辑 `frontend/src/client/**` 和 `frontend/src/routeTree.gen.ts`。

## Risks & Rollout
- 文档文件名当前包含中文与空格，slug 设计必须稳定并与前端路由参数兼容。
- 运行环境需要能读取仓库中的 `docs/rules/` 目录；若未来部署产物不包含文档文件，需要再定义打包策略。
- MVP 先按纯文本展示，后续如果引入 Markdown 渲染，需要额外处理样式和安全策略。
