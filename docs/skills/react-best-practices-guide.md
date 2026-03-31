# react-best-practices 使用说明

## 结论

`react-best-practices` 适合当前仓库，但它在本项目中的定位应是：

- 以项目 React 规范为主
- 以 `react-best-practices` 作为 React 性能优化与 review 规则集
- 不把它当作脱离项目上下文的通用硬规范

原因很直接：当前仓库是 `Vite + React 19 + TanStack Query + TanStack Router + FastAPI OpenAPI client` 的前后端分离 SPA，不是 Next.js / RSC 项目。

因此，React 相关判断应先服从本仓库已有约束，再决定是否引入 skill 中的性能优化规则。

## 当前项目的适配前提

当前前端以如下约束为准：

- 技术栈：React 19 + Vite 7 + TypeScript + TanStack Query + TanStack Router
- 数据访问：优先复用 `frontend/src/client/**` 的生成式 OpenAPI client
- 代码风格：Biome 统一格式，双引号，按需分号
- 导入约束：优先 `type` import，业务代码使用 `@/` alias
- 禁改边界：`frontend/src/client/**`、`frontend/src/routeTree.gen.ts`、`frontend/src/components/ui/**`

这意味着本项目的 React 规范，不只是“性能更优”，还包括：

- 与后端 OpenAPI schema 的协作方式
- 与 TanStack Query 的数据获取方式
- 与 TanStack Router 的路由组织方式
- 与生成代码边界的协作方式

## 适用场景

当你需要下面这些事情时，适合优先使用它：

- 做 React 性能 review
- 重构 React 组件，减少无效渲染
- 优化请求瀑布和加载链路
- 排查包体积过大或前端加载慢的问题
- 审查页面是否过度依赖 `useEffect`

## 它在本项目中真正应该推动的改法

在当前仓库里，这个 skill 最适合推动下面这些优化：

- 独立异步请求优先并发执行，例如用 `Promise.all()`
- 避免对重量级库使用不必要的 barrel import
- 客户端数据获取优先沿用 `TanStack Query`
- 对昂贵初始值使用惰性状态初始化
- 对非紧急 UI 更新使用 `startTransition`
- 避免仅为同步派生值而引入额外 `useEffect`

## 不应机械照搬的方向

以下做法不应由这个 skill 单独决定：

### 1. 不应替代项目 React 主规范

如果 skill 建议和仓库既有约束冲突，以项目规范为准，例如：

- `@/` alias
- `type` import
- Biome 风格要求
- 生成代码禁止直接编辑

### 2. 不应脱离后端协作上下文做“纯前端最优”

当前仓库的前端不是独立前端工程，很多实现都受 FastAPI OpenAPI schema 驱动。

因此不能只因为某种前端写法“更优雅”就绕开：

- 生成式 client
- 现有 query key 组织
- 既有路由与鉴权流程

### 3. 不应把可选优化当作强制规则

像下面这些更适合按场景采用，而不是一刀切要求：

- `content-visibility: auto`
- SVG 动画包裹层优化
- JavaScript 微优化
- 为了避免 re-render 而过度拆组件

如果代码本身并不在热路径上，这类规则不应压过可读性和维护性。

## 使用方法

### 方法 1：直接在对 Codex 的请求里点名

```text
使用 react-best-practices review 这次前端改动，但以当前仓库 React 规范为主。
```

```text
使用 react-best-practices 优化这个 React 页面性能，重点看请求瀑布和无效重渲染。
```

### 方法 2：先查看 skill 原文

```bash
npx openskills read react-best-practices
```

## 推荐提问模板

```text
使用 react-best-practices review 这次前端改动，重点检查异步 waterfall、bundle 体积和不必要的 re-render，但不要脱离当前仓库的 TanStack Query / Router / OpenAPI client 结构。
```

```text
使用 react-best-practices 重构这个页面，优先处理独立请求串行执行、重量级 import 和昂贵状态初始化问题，同时保持项目现有路由与数据层模式。
```

```text
使用 code-standards 和 react-best-practices 一起 review 这个 React 页面，先找逻辑问题，再看性能问题。
```

## 与 vercel-react-best-practices 的关系

- 当前仓库若是普通 Vite SPA React 任务，优先参考 `react-best-practices`
- `vercel-react-best-practices` 只适合作为补充参考，不应默认套用
- 涉及 Next.js、RSC、服务端组件边界、服务端缓存语义时，再单独引入 `vercel-react-best-practices`

## 在本项目中的建议

- 这是当前仓库最适合用于通用 React 性能 review 的 skill
- 它应作为“项目 React 规范之后的第二层规则”
- 若 skill 原文和项目代码现状冲突，以项目现有前端架构和仓库约束为准
