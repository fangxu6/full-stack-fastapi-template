# Interface Spec - Backend 重构补档

## Overview
- 对外 HTTP API 保持兼容；当前 `items` 继续使用轻量 CRUD 路由。
- 鉴权方式、错误返回格式沿用现有 FastAPI 实现。
- `api/deps.py` 继续作为依赖入口，内部转发到 `api/dependencies/*`。

## Internal Contracts

### Route -> Service
- Route 层职责：参数解析、依赖注入、响应模型声明、HTTP 状态码映射。
- Service 层职责：业务规则校验、流程编排、跨 CRUD/repository 协调、外部副作用触发。

### Service -> CRUD/Repository
- Service 通过 CRUD 或模块 repository 完成原子持久化操作。
- CRUD/repository 层仅负责数据库交互，不承载业务规则与外部 I/O。

### Model <-> Schema
- `models/`：数据库表与持久化结构。
- `schemas/`：请求/响应 DTO（如 user/item/security）。
- 通过分层隔离，避免将 DB 结构直接暴露为 API 契约。

## Public API Compatibility
- Users/login 路径与方法保持不变。
- Items 路径保持 `/api/v1/items/*`，暂不挂到 `/modules` 命名空间。
- 请求/响应主体语义：保持兼容；不引入新版本号。
- 错误语义：沿用既有状态码与异常细节结构。

## Notes
- 当前项目主要停留在业务 CRUD 层面，items 暂不升级为完整模块边界。
- 后续若新增业务能力，应优先在 service 层扩展并同步 schema，而非回退到 route 直连 CRUD。
