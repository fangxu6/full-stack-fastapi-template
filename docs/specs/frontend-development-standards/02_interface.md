# Interface Spec - 前端开发规范

## Overview
- 本次交付主要是文档接口，不新增运行时 API。
- 规范文档面向前端开发者、评审者和 AI 代码代理，作为后续实现的统一输入。

## Output Contract

### New Document
- `docs/rules/前端开发规范.md`
- 内容类型：中文 Markdown
- 目标读者：本仓库前端开发者

### Document Sections
- 适用范围与技术栈
- 工具链与基础约束
- 目录职责与文件组织
- TypeScript / React 编码约定
- 路由、页面、鉴权与状态边界
- React Query / OpenAPI Client 使用规则
- 表单、错误处理、加载态和空态规范
- UI、样式、主题与可访问性要求
- 测试、构建、联调与提交流程
- 开发自检清单

## Public Compatibility
- 不影响现有 HTTP API、前端路由或构建入口。
- 不调整 `frontend/package.json`、`frontend/biome.json`、`frontend/tsconfig.json` 的外部行为。

## Referenced Source of Truth
- `frontend/package.json`
- `frontend/biome.json`
- `frontend/tsconfig.json`
- `frontend/src/main.tsx`
- `frontend/src/routes/**`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/components/**`
