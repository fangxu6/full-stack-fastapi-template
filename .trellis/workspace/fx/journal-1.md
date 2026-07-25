# Journal - fx (Part 1)

> AI development session journal
> Started: 2026-05-16

---



## Session 1: 完成 CRM 入库与出货 MVP

**Date**: 2026-07-16
**Task**: 完成 CRM 入库与出货 MVP
**Branch**: `master`

### Summary

完成 R-006/R-007 收尾：历史单据保护、导入事务回滚、迁移对账期初与库存键非负余额测试；库存 API 22 passed、导入器 18 passed、完整后端 137 passed 1 skipped；backend/scripts/lint.sh、前端 lint/build、库存 Chromium E2E 3 passed；任务已归档。

### Main Changes

- Added an ADR and domain glossary that separate technical primary keys, business identifiers, and resource access domains.
- Updated PostgreSQL, API, and Trellis backend guidance for new `BIGINT GENERATED ALWAYS AS IDENTITY` entity keys while retaining UUID foreign keys to existing resources.
- Defined payload rejection, authorization semantics, UUID exceptions, and the JavaScript safe-integer operational alert.

### Git Commits

| Hash | Message |
|------|---------|
| `54db6d0` | (see git log) |
| `c38f84d` | (see git log) |
| `15c4886` | (see git log) |

### Testing

- Passed scoped Markdown link resolution and `git diff --check`.
- Validated the SQLModel `BigInteger` plus `Identity(always=True)` metadata example with the backend environment.
- Backend lint, typing, and test suites were not run because this task changed documentation only.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: Adopt BIGINT identity primary-key policy

**Date**: 2026-07-20
**Task**: Adopt BIGINT identity primary-key policy

### Summary

Defined a forward-only PostgreSQL BIGINT GENERATED ALWAYS AS IDENTITY primary-key policy, including UUID compatibility, API validation, access semantics, and JavaScript precision alerting.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `979cf39` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: Inventory unit remote search

**Date**: 2026-07-22
**Task**: Inventory unit remote search
**Branch**: `master`

### Summary

Replaced fixed 100-row inventory unit selects with 20-row debounced server search, added isolated UI coverage beyond 100 units, and documented the frontend rule.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `c1bbd13` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: Trellis workflow planning safeguards

**Date**: 2026-07-22
**Task**: Trellis workflow planning safeguards
**Branch**: `master`

### Summary

Added complex-plan grilling, API E2E planning artifacts, and a tested spec wiki catalog, log, and lint maintenance loop localized to the FastAPI/React Docker Compose runtime.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `c0044fc` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 5: Remove Docker assumptions from Trellis guidance

**Date**: 2026-07-22
**Task**: Remove Docker assumptions from Trellis guidance
**Branch**: `master`

### Summary

Removed Docker/Compose release and default-validation instructions from Trellis workflow and non-sidecar specs; preserved isolated-environment requirements and the active sidecar contract; added regression coverage and validated the spec catalog.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `12ad458` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 6: Document validation request IDs

**Date**: 2026-07-22
**Task**: Document validation request IDs
**Branch**: `master`

### Summary

Regenerated the frontend OpenAPI client, documented required request_id on validation errors, and added backend regression coverage.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `f92be66` | (see git log) |
| `8652a35` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 7: Implement RBAC authorization foundation

**Date**: 2026-07-22
**Task**: Implement RBAC authorization foundation
**Branch**: `master`

### Summary

Delivered database-backed multi-role RBAC for user administration and inventory, including permission catalog, role lifecycle safeguards, protected routes, frontend guards and role management UI, recovery runbook, and validation coverage.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `22ea217` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 8: 完成路由质量策略与 RBAC 修复

**Date**: 2026-07-23
**Task**: 完成路由质量策略与 RBAC 修复
**Branch**: `master`

### Summary

完成 thin route AST 校验、Dashboard 页面迁移、RBAC review findings 修复与相关回归验证；归档 07-23-route-quality-policy。验证包括 AST/Hook/后端 55 项测试、前端类型与 Biome、权限 Playwright E2E 6 项。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `7ea51b2` | (see git log) |
| `4d41059` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 9: 清理存量厚路由并统一路由结构

**Date**: 2026-07-23
**Task**: 清理存量厚路由并统一路由结构
**Branch**: `master`

### Summary

将 rules 与 reset-password 的搜索状态读取迁移至所属平台页面，路由仅保留配置；新增全量路由 AST 库存回归，所有当前路由通过。类型、Biome、质量钩子和 AST 测试通过。用户明确暂时延后 API/MailCatcher 支持的重置密码 E2E。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `ded9537` | (see git log) |
| `b44644e` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 10: Implement structured observability

**Date**: 2026-07-23
**Task**: Implement structured observability
**Branch**: `master`

### Summary

Added structlog NDJSON events, request correlation, safe dependency/startup telemetry, Sentry scrubbing, and backend observability tests.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `e369923` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 11: 定义未来告警契约

**Date**: 2026-07-25
**Task**: 定义未来告警契约
**Branch**: `master`

### Summary

评估并批准未来运维告警设计：业务触发、Webhook 主通道与邮件兜底；首个具体场景再引入 Celery、Redis 和 PostgreSQL outbox。明确区分运维告警与应用用户待办通知，并归档评估任务。

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `efb238b` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 12: Add daily inventory email reports

**Date**: 2026-07-25
**Task**: Add daily inventory email reports
**Branch**: `master`

### Summary

Implemented scheduled prior-day inventory report snapshots, per-recipient SMTP delivery retries, migration, configuration, documentation, and full verification.

### Main Changes

- Detailed change bullets were not supplied; see the summary above.

### Git Commits

| Hash | Message |
|------|---------|
| `db4c591` | (see git log) |

### Testing

- Validation was not recorded for this session.

### Status

[OK] **Completed**

### Next Steps

- None - task complete
