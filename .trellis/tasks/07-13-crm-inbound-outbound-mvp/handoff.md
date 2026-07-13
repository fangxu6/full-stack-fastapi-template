# CRM 入库与出货 MVP 续作交接

## Current State

- 任务状态：`in_progress`。
- 已完成：库存 ORM/Alembic、主数据、来料入库/坯布退走/成品出货 API、库存余额和关联台账查询、四组前端路由与页面骨架、OpenAPI 客户端生成。
- 已通过：库存 API 回归测试、后端 Ruff、迁移升级、前端 TypeScript 和 Biome lint。

## Known Blockers

### Frontend Router Dependency

`bun run dev` 和 `bun run build` 均在依赖预构建阶段失败：

```text
@tanstack/router-core/scroll-restoration-script is not exported
```

当前安装版本包括 `@tanstack/react-router 1.170.15`、
`@tanstack/router-core 1.171.13`、`@tanstack/router-plugin 1.168.18`。
需先统一兼容的 TanStack Router 版本集合，再继续 UI 验收。

### Historical Workbook Input

PRD 中分析过的两份 `hongxia` Excel 文件不在当前工作区，不能完成导入器的实际映射和余额对账。恢复工作时先提供只读副本，并在隔离数据库运行。

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
