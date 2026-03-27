# tailwind-best-practices 使用说明

## 作用

`tailwind-best-practices` 是一个 Tailwind 样式规范类 skill，重点在于控制样式一致性、避免设计 token 漂移，以及限制随意覆盖组件样式。

## 适用场景

当你需要下面这些事情时，可以使用它：

- 检查 Tailwind 类名写法是否规范
- 检查是否应该复用现有组件
- 检查是否滥用了任意值
- 审查组件样式是否偏离设计系统

## 使用方法

### 方法 1：直接在对 Codex 的请求里点名

```text
使用 tailwind-best-practices review 这个组件的样式改动。
```

```text
使用 tailwind-best-practices 检查这个页面有没有乱用 Tailwind class。
```

### 方法 2：先查看 skill 原文

```bash
npx openskills read tailwind-best-practices
```

## 推荐提问模板

```text
使用 tailwind-best-practices review 这个组件，重点检查 token 使用、任意值和 className 覆盖问题。
```

```text
使用 tailwind-best-practices 作为参考来重构这个页面样式，但要适配当前仓库的前端结构。
```

## 它会重点检查什么

这个 skill 的关注点主要是：

1. 优先复用已有组件
2. 优先使用已有设计 token
3. 避免随意写任意值
4. 限制对设计系统组件的 `className` 覆盖

## 重要限制

这个 skill 原本面向的是 Mastra Playground 的包结构：

- `packages/playground-ui`
- `packages/playground`

这些目录并不存在于当前仓库。

## 在本项目中的建议

- 把它当作“Tailwind 约束参考”使用，不要机械照搬它的目录和组件规则。
- 它最可迁移的价值是：
  - 优先复用组件
  - 避免随意扩展 token
  - 保持 class 使用风格一致
- 真正落地时，要以当前项目 `frontend/` 下的实际组件和样式体系为准。
