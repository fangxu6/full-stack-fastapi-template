# react-best-practices 使用说明

## 作用

`react-best-practices` 是一个 React 性能优化类 skill，重点覆盖异步请求瀑布、包体积、客户端数据获取、重渲染、渲染开销和部分 JavaScript 热路径问题。

## 适用场景

当你需要下面这些事情时，适合优先使用它：

- 做 React 性能 review
- 重构 React 组件，减少无效渲染
- 优化请求瀑布和加载链路
- 排查包体积过大或前端加载慢的问题

## 使用方法

### 方法 1：直接在对 Codex 的请求里点名

```text
使用 react-best-practices 优化这个 React 页面性能。
```

```text
使用 react-best-practices review 这个组件树，重点看重渲染和请求瀑布。
```

### 方法 2：先查看 skill 原文

```bash
npx openskills read react-best-practices
```

## 推荐提问模板

```text
使用 react-best-practices review 这次前端改动，重点检查异步 waterfall、bundle 体积和不必要的 re-render。
```

```text
使用 react-best-practices 重构这个页面，优先处理独立请求串行执行、重量级 barrel import 和昂贵状态初始化问题。
```

```text
使用 code-standards 和 react-best-practices 一起 review 这个 React 页面。
```

## 它的优先级顺序

这个 skill 通常按下面顺序考虑优化收益：

1. 消除异步 waterfall
2. 降低 bundle 体积
3. 改善客户端数据获取
4. 减少不必要的重渲染
5. 优化渲染性能
6. 在值得时做 JavaScript 微优化

## 它常推动的改法

典型建议包括：

- 独立异步请求用 `Promise.all()`
- 避免对重量级库使用 barrel import
- 为客户端请求增加去重策略
- 对昂贵初始值使用惰性状态初始化
- 对非紧急更新使用 `startTransition`

## 在本项目中的建议

- 这是这 5 个新 skill 里，对当前仓库前端最直接有用的一个。
- 它和仓库已有的 `vercel-react-best-practices` 可以互补使用。
- 如果任务偏通用 React 性能优化，用它更合适。
- 如果任务涉及更强的 React/Next 服务端与客户端边界约束，再结合 `vercel-react-best-practices`。
