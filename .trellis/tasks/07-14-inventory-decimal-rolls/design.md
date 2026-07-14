# 匹数小数精度技术设计

## Data Contract

`inventory_document_line.quantity_rolls` 与 `inventory_ledger_entry.rolls_delta` 改为 PostgreSQL `NUMERIC(18,2)` 和 Python `Decimal`。匹数写入 DTO 采用大于零、两位小数的约束；读取 DTO 不继承写入 DTO，并允许历史零值。余额 DTO 与台账 DTO 同步改为 Decimal，以保持 API、生成客户端和 React Query 数据链一致。

## Migration And Repair

新迁移先将两列转换为 `NUMERIC(18,2)`，保留现有非负约束。随后扫描当前 `legacy_import_row.raw_cells` 中存在两位以内小数匹数的行，按来源行关联的业务明细和台账修复被截断的数量。

对于已存在同源 `MIGRATION_RECONCILIATION_OPENING` 的出库记录，迁移将同一匹数差额加到期初正变动并写入单据明细和负台账变动，使该事件之后的余额保持不变且不为负。当前预期修复三泰第 532、538 行。迁移仅处理可从原始 JSON 确认的小数差额；不存在来源证据的零匹数历史记录维持原值。

`downgrade()` 在发现任一匹数列存在非整值时抛出明确异常，禁止隐式向整数转换；只有不存在小数时才允许恢复整数列。

## Service And Importer

服务层的台账写入、库存不足检测和余额聚合都使用 `Decimal("0")` 作为匹数初始值。导入器直接写入 `Decimal` 匹数和匹数差额，迁移对账期初也保留同一精度。

## Frontend

`DocumentEditorModal` 的匹数输入统一使用 `min=0.01`、`step=0.01`、`precision=2`。生成客户端是唯一 API 类型来源；前端不手写匹数传输类型。列表、台账和余额显示服务端返回的小数值，不进行客户端再舍入。
