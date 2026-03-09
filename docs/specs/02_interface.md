# Interface Spec - Backend 重构补档

## Overview
- 对外 HTTP API 保持兼容；本次重点是内部接口与模块边界重塑。
- 鉴权方式、错误返回格式沿用现有 FastAPI 实现。
- `api/deps.py` 继续作为依赖入口，内部转发到 `api/dependencies/*`。

## Internal Contracts

### Route -> Service
- Route 层职责：参数解析、依赖注入、响应模型声明、HTTP 状态码映射。
- Service 层职责：业务规则校验、流程编排、跨 CRUD 协调、外部副作用触发。

### Service -> CRUD
- Service 通过 CRUD 完成原子持久化操作。
- CRUD 层仅负责数据库交互，不承载业务规则与外部 I/O。

### Model <-> Schema
- `models/`：数据库表与持久化结构。
- `schemas/`：请求/响应 DTO（如 user/item/security）。
- 通过分层隔离，避免将 DB 结构直接暴露为 API 契约。

## Public API Compatibility
- Endpoint 路径与方法：保持不变（users/login/items 相关路由）。
- 请求/响应主体语义：保持兼容；不引入新版本号。
- 错误语义：沿用既有状态码与异常细节结构。

## Notes
- 本次变更是“实现重构”而非“接口升级”。
- 后续若新增业务能力，应优先在 service 层扩展并同步 schema，而非回退到 route 直连 CRUD。
