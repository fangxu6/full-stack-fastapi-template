# CRM 入库与出货 MVP 续作交接

## Current State

- 任务状态：`in_progress`。
- 已完成：库存 ORM/Alembic、主数据、来料入库/坯布退走/成品出货 API、库存余额和关联台账查询、四组前端路由与页面骨架、OpenAPI 客户端生成；单据页已接入日期、加工单位、收货单位和单号筛选。
- 已完成历史导入：真实两份工作簿可读取；导入器支持标题/双层表头、退走单位、负数出货、仅米数历史行、库存快照、迁移对账期初和导入防重。隔离 PostgreSQL 库完成 dry-run 与实际导入：3,949 条来源行、3,850 条台账记录、3,531 条待清洗、501 条对账期初，来料与成品余额均无负数。
- 已通过：3 个库存 API 回归测试、6 个导入器测试、导入器 Ruff/mypy/ty、前端 TypeScript 和生产构建。

## Known Blockers

### Frontend Router Dependency

此前的 Router 依赖问题未在当前环境复现；`bun run build` 已成功完成。仍需补实际浏览器 E2E 场景。

### Historical Workbook Input

两份 `hongxia` Excel 文件位于工作区，且已在隔离数据库完成实际导入验证。不要在迁移链失配的主本地数据库执行导入：其 `alembic_version` 为仓库不存在的 `20260410_add_rbac_foundation`；应先恢复该数据库的 Alembic 历史，或使用干净数据库升级到 `c9b1f4e7a2d0`。

## Resume Commands

```powershell
python ./.trellis/scripts/get_context.py
python ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex

Set-Location backend
uv run pytest tests/api/routes/test_inventory.py -q
uv run ruff check app/modules/inventory app/models/inventory.py app/schemas/inventory.py

Set-Location ../frontend
bun run lint
bun run build
```

导入命令的预期形式：

```powershell
Set-Location backend
uv run python scripts/import_inventory.py `
  --actor-user-id <UUID> `
  --raw-workbook <raw.xlsx> `
  --finished-workbook <finished.xlsx> `
  --dry-run
```

实际导入前必须先完成 `deferred-iterations.md` 的 R-001 至 R-003，并保留 dry-run 对账报告。

## Primary Files

- `backend/app/modules/inventory/service.py`
- `backend/app/modules/inventory/importer.py`
- `backend/scripts/import_inventory.py`
- `frontend/src/features/inventory/`
- `frontend/src/routes/_layout/inventory/`
- `deferred-iterations.md`
