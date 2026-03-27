# Test Spec - 前端开发规范

## Validation Scope
- 验证新增规范文档是否准确反映当前前端实现与工具链。
- 验证文档中新增约束是否与仓库级规则一致。

## Review Checklist
- TC1: 文档中描述的技术栈与 `frontend/package.json` 一致。
- TC2: 文档中的格式化与静态检查要求与 `frontend/biome.json`、`frontend/tsconfig.json` 一致。
- TC3: 文档中的路由、查询、表单和组件分层描述能在现有代码中找到对应示例。
- TC4: 文档明确标注生成文件不可手改。
- TC5: 文档中的开发命令与 `frontend/README.md`、`package.json` 脚本一致。
- TC6: 文档显式纳入 `.agents/skills/react-best-practices/` 中适用于本项目的规则，包括 `Promise.all()`、TanStack Query 去重、lazy state init、`startTransition` / `useEffectEvent`、bundle 控制和热点路径约束。
- TC7: 文档没有直接照搬不适用于当前仓库的框架专属模式，规则表述与 Vite + React 19 + TanStack Query 实际栈相容。

## Manual Verification
- 逐段核对文档中的规范是否可以指导新增页面、表单和 CRUD 流程开发。
- 检查是否存在脱离当前项目实际情况的通用化描述。
- 检查“现有约定”和“增强要求”是否被清晰区分。
- 检查新增性能规则是否既可执行又不过度教条，例如仅在热点路径、重型组件或可感知交互中要求额外优化。
