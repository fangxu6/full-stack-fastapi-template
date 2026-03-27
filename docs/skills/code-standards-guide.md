# code-standards 使用说明

## 作用

`code-standards` 是一个面向代码评审的 skill。它会引导代理按固定检查清单审查改动，优先发现正确性问题、代码质量问题、风格偏差和常见 lint 异味。

## 适用场景

当你需要下面这些事情时，适合使用它：

- 做代码 review
- 做 PR 合并前检查
- 排查潜在 bug 风险
- 统一代码风格和质量标准

## 使用方法

### 方法 1：直接在对 Codex 的请求里点名

```text
使用 code-standards review 这次改动。
```

```text
使用 code-standards 检查这个 PR 有没有必须先修的问题。
```

### 方法 2：先查看 skill 原文

```bash
npx openskills read code-standards
```

## 推荐提问模板

```text
使用 code-standards review frontend 的暂存改动。
```

```text
使用 code-standards review backend 改动，重点找逻辑 bug、边界条件和错误处理问题。
```

```text
使用 code-standards 和 react-best-practices 一起 review 这个 React 页面，重点看 bug 和性能回退。
```

## 它会重点检查什么

通常会按下面顺序推动 review：

1. 先找必须修复的问题
2. 再看整体代码质量
3. 再看风格规范是否一致
4. 最后标出常见异味

典型检查点包括：

- 逻辑错误和行为错误
- 错误处理缺失
- 并发或竞态问题
- 空值、空数组、边界值等漏处理场景
- `console.log`、`debugger`、注释掉的代码
- 魔法数字
- 无 issue 关联的 `TODO` 或 `FIXME`

## 建议输出形式

如果你希望输出稳定，可以这样要求：

```text
使用 code-standards review 这次改动，并按“总结、严重问题、改进建议、正向评价”四部分输出。
```

## 在本项目中的建议

- 这个 skill 适用于 `backend/` 和 `frontend/`。
- Python 代码评审时，建议和 `python-patterns` 搭配使用。
- React 代码评审时，建议和 `react-best-practices` 或 `vercel-react-best-practices` 搭配使用。
- 它引用的是 skill 自带的通用 style guide，不是本仓库专属规范，所以要结合仓库实际约束判断。
