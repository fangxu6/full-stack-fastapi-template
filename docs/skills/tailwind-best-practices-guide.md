# tailwind-best-practices 使用说明

## 结论

`tailwind-best-practices` 不能直接作为当前仓库的前端样式规范执行。

原因不是它的方向错了，而是它面向的是 Mastra Playground 的专用设计系统，和当前仓库的 `frontend/` 技术栈、目录结构、token 来源、组件覆盖方式都不完全一致。

在本仓库中，应把它当作“审查视角参考”，而不是“逐条硬性执行规则”。

## 当前项目的适配前提

当前前端以如下约束为准：

- 技术栈：React 19 + Vite 7 + Tailwind CSS v4 + shadcn/ui + Radix UI
- UI 基础层：`frontend/src/components/ui/**`
- 业务组合层：`frontend/src/components/Common/**` 与其他业务组件目录
- 主题与 token 来源：`frontend/src/index.css` 中的 `@theme inline` 和 CSS 变量
- 禁改边界：`frontend/src/components/ui/**` 视为受上游工具管理的基础组件层

这意味着本项目并不存在 skill 原文假设的：

- `packages/playground-ui`
- `packages/playground`
- `@playground-ui/ds/components/*`
- `@playground-ui` 下的 `tailwind.config.ts` token 体系

## 适用场景

当你需要下面这些事情时，可以把它作为参考：

- 检查是否应该优先复用现有 UI primitives
- 检查业务代码是否偏离当前项目的语义 token 和样式风格
- 检查是否存在无必要的十六进制颜色、零散像素值和样式漂移
- 审查页面或组件是否过度覆盖基础 UI 组件样式

## 不应机械照搬的规则

以下规则在当前项目中不应直接原样执行：

### 1. 不应按 `@playground-ui` 组件体系执行

skill 原文要求优先复用 `@playground-ui/ds/components/`。当前项目真正对应的复用目标是：

- `frontend/src/components/ui/**`
- `frontend/src/components/Common/**`

### 2. 不应按 `tailwind.config.ts` token 规则执行

当前项目是 Tailwind v4，语义 token 主要定义在 `frontend/src/index.css`，而不是传统 `tailwind.config.ts`。

因此“只使用 `tailwind.config.ts` token”这条应改写为：

- 优先使用 `bg-background`、`text-foreground`、`bg-primary`、`text-muted-foreground` 这类语义 class
- 颜色、圆角、边框、阴影和主题扩展优先复用 `index.css` 中已经建立的变量体系

### 3. 不应一刀切禁止 arbitrary values

当前项目已经大量使用 shadcn/Radix/Tailwind v4 的合法模式，例如：

- `focus-visible:ring-[3px]`
- `top-[50%]`
- `max-w-[calc(100%-2rem)]`
- `w-(--radix-dropdown-menu-trigger-width)`
- `p-[3px]`

这类写法在当前项目里是正常且必要的，不能按“除高宽外全部禁止”的规则处理。

### 4. 不应禁止对基础 UI 组件传 `className`

当前仓库的 `components/ui/**` 基础组件本身就是按 shadcn 模式实现，允许通过 `className` 做受控扩展和组合。

因此不能把“禁止给 DS 组件传 `className`”当成硬规则。更合理的要求是：

- 优先使用已有 `variant`、`size`、`data-*` 状态和组合能力
- 当现有 API 无法表达需求时，允许在业务层通过 `className` 做有限扩展
- 不要为了局部页面需求去反复改动 `components/ui/**` 基础层

## 在本项目中真正应该执行的版本

把这个 skill 转译到当前仓库后，应执行下面这些规则。

### 1. 优先复用现有组件

- 不在业务目录重复造按钮、输入框、弹窗、表格、下拉等基础组件
- 优先复用 `frontend/src/components/ui/**`
- 通用展示与布局优先复用 `frontend/src/components/Common/**`

### 2. 优先使用现有语义 token

- 优先使用 `background`、`foreground`、`primary`、`muted`、`accent`、`border`、`ring` 等语义 token
- 尽量避免直接写十六进制颜色、孤立的 RGB/OKLCH 值
- 新视觉需求先看 `frontend/src/index.css` 是否已有合适变量，不要先加临时颜色

### 3. 对 arbitrary values 采用“限缩使用”而不是“全面禁止”

允许：

- Radix 相关尺寸和定位变量
- `calc(...)`、CSS 变量和对齐类表达式
- shadcn 默认 primitives 已使用的 bracket 语法
- 组件确有必要的精确尺寸、定位、动画参数

不推荐：

- 无明确理由的 `text-[15px]`、`mt-[17px]`、`rounded-[5px]`
- 业务层随手写的 `bg-[#xxxxxx]`、`border-[#xxxxxx]`
- 只为凑视觉效果而堆积零散像素值

### 4. 对 `className` 覆盖采用“先复用 API，再有限扩展”

优先顺序应为：

1. 先看基础组件是否已有 `variant` / `size`
2. 再看是否可以通过外层布局解决，而不是改组件内部视觉
3. 最后才在业务层传入必要的 `className`

以下情况通常是合理的：

- 控制尺寸，例如 `h-8 w-8`
- 控制布局，例如 `w-full`、`max-w-xs`、`justify-end`
- 控制特定容器对齐或响应式行为

以下情况应谨慎：

- 直接改基础组件的主色、边框体系、交互反馈风格
- 用局部 `className` 把同一个组件改成另一套视觉语言

## 推荐使用方法

### 方法 1：把它当“参考约束”点名使用

```text
使用 tailwind-best-practices review 这个组件样式，但按当前仓库的 shadcn/Tailwind v4 结构适配，不要照搬 Mastra 规则。
```

```text
使用 tailwind-best-practices 检查这个页面是否复用了现有 ui 组件、是否乱写颜色和无意义 arbitrary values。
```

### 方法 2：先查看 skill 原文，再按本项目规则落地

```bash
npx openskills read tailwind-best-practices
```

然后以本文件和 `docs/rules/前端开发规范.md` 为准做项目化解释。

## 推荐提问模板

```text
使用 tailwind-best-practices review 这个组件，重点检查：
1. 是否应该复用 frontend/src/components/ui 现有组件
2. 是否偏离 src/index.css 的语义 token
3. 是否有无必要的十六进制颜色和零散 arbitrary values
4. className 扩展是否超出了业务层应有范围
```

## 与本仓库其他规范的关系

- 样式落地时，以 `docs/rules/前端开发规范.md` 为主规范
- `tailwind-best-practices` 只提供审查视角，不替代仓库主规范
- 若 skill 原文与当前仓库现状冲突，以当前仓库前端技术栈和现有代码模式为准
