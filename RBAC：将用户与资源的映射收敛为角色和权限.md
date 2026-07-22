---
okf_version: "0.1"
type: Concept
title: "RBAC：将用户与资源的映射收敛为角色和权限"
description: "以角色作为用户与权限之间的稳定中介，降低企业系统授权配置与审计的复杂度。"
resource: "https://www.woshipm.com/pd/5576757.html"
okf_bundle: ""
catalog_path: ""
source_note: ""
tags:
  - product/permission-design
  - security/access-control
  - architecture/rbac
timestamp: 2026-07-22T00:00:00+08:00
aliases:
  - "基于角色的访问控制"
  - "Role-Based Access Control"
---

# RBAC：将用户与资源的映射收敛为角色和权限

## Summary

RBAC（Role-Based Access Control）不直接为每个用户逐项授予资源访问权，而是先将权限赋给代表岗位职责的角色，再将用户分配给角色。它适合角色相对稳定、用户和资源规模持续增长的企业后台系统，可将大量用户-资源的直接映射收敛为用户-角色与角色-权限两类关系。[1][2]

在产品设计中，RBAC 不能只等同于菜单显隐：功能权限决定能否进入页面或执行操作，数据权限决定进入后可见、可处理的数据范围。前端的隐藏与禁用只是体验层，服务端仍须对每个受保护请求执行授权检查。[1][3]

## Claims

- 角色是授权管理的中介层：用户可拥有一个或多个角色，角色承载权限；这比逐用户维护 ACL 更贴近组织岗位，也更容易批量调整与审计。[1][2]
- 核心 RBAC 至少需要用户-角色分配和权限-角色分配；角色层级、静态职责分离与动态职责分离是可按业务需要叠加的模型能力。[2]
- 权限粒度应由风险和业务决策决定，而不是越细越好。将相近操作组合为面向业务的权限点，能降低配置负担；高风险职责则应以互斥、审批或会话激活约束处理。[1][2]
- 授权应遵循最小权限与默认拒绝，并在每一次受保护资源访问时由可信服务端验证，而不能依赖客户端页面、路由或按钮状态。[3]

## Mechanism

1. **定义资源与动作**：为菜单、页面、按钮/API、业务对象及敏感字段建立稳定的权限标识；先区分功能权限和数据范围。
2. **进行角色工程**：从业务流程和岗位职责列出候选角色，识别共享、继承与互斥关系，并决定哪些角色内置、哪些可自定义。[1][2]
3. **绑定与计算授权**：将权限赋给角色、将角色赋给用户；有层级时计算继承，有职责分离时校验冲突，并在请求时计算当前会话的有效权限。
4. **叠加数据约束**：在获得功能许可后，再按对象、行、列或组织范围过滤数据。需要时间、地点、设备或资源属性等动态条件时，RBAC 可与 ABAC/关系型策略组合，而不是强行把所有条件编码为角色。[1][3]
5. **治理与验证**：默认拒绝、记录授权决策，随角色、组织或资源变化复核权限；为越权、横向访问和职责冲突建立集成测试。[3]

## Evidence

- NIST 将 RBAC 描述为通过用户、角色、权限、操作和对象等元素及其关系管理授权；其标准模型包含 Core RBAC、Hierarchical RBAC、静态职责分离和动态职责分离四个组件。[2]
- 原文以企业后台产品为中心，区分菜单/按钮等功能权限与对象、行、列等数据权限，并给出角色、用户、部门、职位、菜单与版本配置的设计路径。[1]
- 原文关于「部门或职位也可直接绑定功能权限」是产品建模建议，不是 RBAC 标准要求。它同时提醒同一类功能权限最好只绑定一个主要实体，以避免多来源配置难以解释；应结合实际组织与审计需求验证。[1]
- OWASP 建议默认拒绝、最小权限，以及在每次请求时验证权限。这些是安全执行要求，补足了产品配置页面通常不会覆盖的后端边界。[3]

## Local Implication

在设计 WMS、MES 或其他管理后台时，先维护一张「角色 × 功能权限 × 数据范围」矩阵，再讨论角色管理、菜单管理与页面交互。将权限标识定义为后端可验证的契约，前端据此做导航和按钮呈现；不要把前端隐藏当作授权。涉及部门层级、数据归属或跨部门协作时，应把数据范围作为角色的独立属性或策略配置，而非复制出大量仅为数据范围不同的角色。

## Links

- [[小型公司 WMS 设计、选型与落地全攻略]]
- [[WMS 表结构设计：从开发视角看轻量化与可扩展]]
- [[Ant Design：企业级中后台 UI 设计系统]]

## Citations

[1] [万字长文：深入浅出 RBAC 权限设计](https://www.woshipm.com/pd/5576757.html)，产品乱弹，2022-08-25。

[2] [Role Based Access Control](https://csrc.nist.gov/projects/role-based-access-control)，NIST Computer Security Resource Center。

[3] [Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)，OWASP Cheat Sheet Series。

## Optional Structured Data

```json
{
  "@context": "https://schema.org",
  "@type": "DefinedTerm",
  "name": "Role-Based Access Control",
  "description": "通过角色将用户与权限关联的访问控制模型。",
  "sameAs": [
    "https://csrc.nist.gov/projects/role-based-access-control"
  ]
}
```
