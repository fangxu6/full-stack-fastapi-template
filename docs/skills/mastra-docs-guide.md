# mastra-docs 使用说明

## 作用

`mastra-docs` 是一个文档写作类 skill，原本用于 Mastra 项目的文档体系。它强调文档结构、写作风格、文档分类和 lint 约束。

## 适用场景

当你需要下面这些事情时，可以参考它：

- 重写技术文档
- 提升说明文档的结构清晰度
- 统一文档语气和风格
- 把零散说明整理成更规范的文档

## 使用方法

### 方法 1：直接在对 Codex 的请求里点名

```text
使用 mastra-docs 重写这份功能说明文档。
```

```text
使用 mastra-docs 的写法风格整理 docs/specs 里的内容。
```

### 方法 2：先查看 skill 原文

```bash
npx openskills read mastra-docs
```

## 推荐提问模板

```text
使用 mastra-docs 重写 docs/specs/feature-template/01_requirement.md，让结构更清晰、语言更统一。
```

```text
使用 mastra-docs 作为写作参考，但要适配当前仓库的 docs 目录，不要照搬 Mastra 的路径规范。
```

## 它会重点推动什么

这个 skill 会推动代理：

- 先看文档类型，再决定写法
- 按文档类别组织内容
- 注意格式、Markdown lint 和 prose lint
- 使用更稳定、更一致的技术文档语气

## 重要限制

这个 skill 原本假定的是 Mastra 自己的文档目录，例如：

- `docs/styleguides/`
- `docs/src/content/en/`

这些路径并不对应当前仓库。

## 在本项目中的建议

- 在本项目里，建议把它当作文档写法参考，而不是直接照着它的目录约定执行。
- 它更适合帮助你改进“怎么写”，不适合直接决定“写到哪里”。
- 如果你只是想要一份更专业、更统一的技术文档，这个 skill 仍然有参考价值。
