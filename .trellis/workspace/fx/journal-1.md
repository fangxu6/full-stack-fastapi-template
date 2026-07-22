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
