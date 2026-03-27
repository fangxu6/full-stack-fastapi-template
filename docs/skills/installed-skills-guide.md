# 已安装 Skill 使用总览

本文汇总当前项目中新安装的 5 个 skill，并给出各自的中文使用说明入口。

## 在本项目中的使用方式

在这个仓库里，skill 常见有两种用法：

1. 在对 Codex 的请求里直接点名 skill。
2. 用 `openskills` 命令读取 skill 原文，先看规则再使用。

## 命令用法

查看单个 skill：

```bash
npx openskills read code-standards
```

一次查看多个 skill：

```bash
npx openskills read code-standards react-best-practices
```

或：

```bash
npx openskills read code-standards,react-best-practices
```

## 对 Codex 的提问方式

直接在需求里写 skill 名即可，例如：

```text
使用 code-standards review 这次改动。
```

```text
使用 react-best-practices 优化这个 React 页面性能。
```

```text
使用 ralph-plan 先帮我做一个实施计划，再开始改代码。
```

## 已安装 Skill

- [code-standards 使用说明](./code-standards-guide.md)
- [mastra-docs 使用说明](./mastra-docs-guide.md)
- [ralph-plan 使用说明](./ralph-plan-guide.md)
- [tailwind-best-practices 使用说明](./tailwind-best-practices-guide.md)
- [react-best-practices 使用说明](./react-best-practices-guide.md)

## 快速建议

- 代码评审优先用 `code-standards`。
- React 性能、重渲染、请求瀑布优化优先用 `react-best-practices`。
- 需求较大、范围不清时，先用 `ralph-plan` 拆计划。
- `mastra-docs` 更适合作为文档写法参考，不适合机械照搬其目录规范。
- `tailwind-best-practices` 更适合作为 Tailwind 约束参考，需要结合本项目实际前端结构使用。
