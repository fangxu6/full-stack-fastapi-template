# CRM 入库与出货 MVP 技术设计

## 1. 目标与边界

本设计实现两套独立库存台账：来料库存与成品库存。日常操作仅包括来料入库、坯布退走、成品出货，以及加工单位和收货单位的维护；首次部署会一次性导入两份用户提供的 Excel 历史明细。

本设计不实现工艺卡、投产、坯布到成品转换、日常库存调整、成品入库页面、可重复的 Excel 导入或报表仪表盘。工艺卡和未来成品入库仅保留可关联的领域扩展点。

## 2. 架构与文件边界

这是一个多实体、跨台账、需要受控导入的业务边界，后端使用明确的 `inventory` 模块，而不是扩展示例 `Item`：

```text
backend/app/
  models/inventory.py                 # ORM 表；不修改 Item 语义
  schemas/inventory.py                # API DTO、分页和输入校验
  modules/inventory/
    router.py                          # 受认证保护的薄路由
    service.py                         # 库存校验、写入、软删/恢复、查询
    repository.py                      # 事务内的持久化与聚合查询
    importer.py                        # 首次 Excel 导入及对账
  api/main.py                          # 注册 inventory router
  alembic/versions/<revision>.py       # 与 ORM 变更配套

frontend/src/
  features/inventory/
    pages/                             # 四组业务页面
    components/                        # 表单、明细编辑器、余额明细抽屉
    api/                               # 由生成 client 组合的请求/查询键
  routes/_layout/inventory*.tsx        # 仅路由定义和页面导入
  app/navigation/menu-config.ts        # 受登录保护的菜单入口
```

ORM 表仍在 `models/*`，HTTP DTO 仍在 `schemas/*`。路由只绑定依赖与响应模型；库存规则、软删除重算和导入编排在模块 service 中。所有 API 继续使用现有认证依赖和统一的 `detail + request_id` 错误契约。

前端所有页面属于 `features/inventory`；路由保持薄，导航只在 `app/navigation/*` 配置。复杂表格、筛选、表单、日期、选择、确认和状态反馈直接使用已挂载 `AntdProvider` 的 Ant Design 6，不引入 `@ant-design/pro-components`，也不改造既有非本功能页面。

## 3. 领域模型和余额规则

### 3.1 主数据

- `ProcessingUnit`：加工单位，名称唯一、可停用；新业务单只能选择有效记录。
- `ReceivingUnit`：收货单位，名称唯一、可停用；成品出货只能选择有效记录。

停用替代物理删除，确保历史记录仍能显示原名称。首次导入从 Excel 的工作表名和加工单位列建立或匹配加工单位；`天双退走` 等值映射为加工单位“天双”加变动类型“退走”。当成品源行的加工单位单元格为空时，以该工作表名作为来源加工单位。不会依据猜测合并名称相近但不完全相同的单位。

### 3.2 物理数据库设计

数据库使用 PostgreSQL、SQLModel 和 Alembic；所有业务表使用 UUID 主键，并继承 [数据库规范的审计字段](../../spec/backend/database-guidelines.md#audit-field-contract)：`created_at`、`created_by`、`updated_at`、`updated_by`、`deleted_at`。表格不再逐项重复这些字段；受控导入命令必须接收并记录实际操作人的 UUID。表名在 ORM 中显式指定，避免依赖类名推导。库存余额不落到可编辑表中，始终由有效日记账聚合得到。

#### 枚举

| PostgreSQL 枚举 | 值 | 用途 |
|---|---|---|
| `inventory_document_type` | `RAW_RECEIPT`、`RAW_RETURN`、`FINISHED_SHIPMENT`、`FINISHED_RECEIPT` | 前三项为日常单据；`FINISHED_RECEIPT` 仅供历史导入和未来成品入库使用，首版没有创建页面。 |
| `inventory_ledger_kind` | `RAW`、`FINISHED` | 区分来料和成品两套不可互相抵扣的台账。 |
| `inventory_movement_type` | `RAW_RECEIPT`、`RAW_RETURN`、`FINISHED_RECEIPT`、`FINISHED_SHIPMENT`、`MIGRATION_RECONCILIATION_OPENING` | 记录库存增减的业务原因；最后一项只允许导入器创建。 |
| `legacy_workbook_kind` | `RAW`、`FINISHED` | 标识两份历史工作簿的来源类型。 |

`inventory_document_type` 与 `inventory_movement_type` 虽有同名值，但职责不同：前者描述单据，后者描述日记账中的库存方向和原因。

#### 主数据表

| 表 | 字段 | 约束与索引 |
|---|---|---|
| `processing_unit` | `id UUID PK`；`name VARCHAR(255)`；`normalized_name VARCHAR(255)`；`is_active BOOLEAN NOT NULL DEFAULT true`；审计字段 | `normalized_name` 唯一，写入前按既定规则去首尾空白并合并连续空白。禁止物理删除被单据引用的记录。 |
| `receiving_unit` | 与 `processing_unit` 相同的字段 | `normalized_name` 唯一；禁止物理删除被单据引用的记录。 |

名称显示使用 `name`，去重和精确匹配使用 `normalized_name`。是否可用于新单据由服务层依据 `is_active` 判断，历史单据不受停用影响。

#### 单据头与明细

三个日常单据共享相同的审计、软删除、筛选和多明细行为，因此采用一张单据头表和一张明细表，而不是六张近似的按类型拆分表。单据类型决定字段校验和库存方向，数据库与服务层共同守住边界。

| 表 | 字段 | 约束与索引 |
|---|---|---|
| `inventory_document` | `id UUID PK`；`document_type inventory_document_type NOT NULL`；`business_date DATE NOT NULL`；`processing_unit_id UUID NOT NULL FK processing_unit`；`receiving_unit_id UUID NULL FK receiving_unit`；`document_number VARCHAR(64) NULL`；`remarks TEXT NULL`；`is_legacy BOOLEAN NOT NULL DEFAULT false`；审计字段 | `CHECK` 要求且仅允许 `FINISHED_SHIPMENT` 填写 `receiving_unit_id`；非历史单据必须有非空白 `document_number`。建立部分唯一索引 `(document_type, document_number) WHERE is_legacy = false`，因此软删除后仍不能复用日常单号，历史空单号和重复单号不受该索引约束。建立 `(document_type, business_date DESC)`、`(processing_unit_id, business_date DESC)` 和 `(receiving_unit_id, business_date DESC) WHERE receiving_unit_id IS NOT NULL` 索引。 |
| `inventory_document_line` | `id UUID PK`；`document_id UUID NOT NULL FK inventory_document`；`line_no SMALLINT NOT NULL`；`item_name VARCHAR(255) NOT NULL`；`item_code VARCHAR(255) NULL`；`wool_content VARCHAR(255) NOT NULL`；`color_code VARCHAR(255) NULL`；`dye_lot_no VARCHAR(255) NULL`；`quantity_rolls INTEGER NOT NULL`；`quantity_meters NUMERIC(18,3) NULL`；审计字段 | `UNIQUE(document_id, line_no)`；`line_no > 0`；`quantity_rolls > 0`；`quantity_meters IS NULL OR quantity_meters > 0`。明细物理删除只允许伴随受控导入回滚；日常删除仅设置单据头的 `deleted_at`。建立 `document_id` 索引。 |

服务层额外验证不可由跨表 `CHECK` 表达的规则：来料明细必须填写 `item_code` 且不得填写颜色、缸号或米数；成品明细必须填写颜色和缸号，日常成品出货必须同时填写匹数和米数；新单据不得写入任何历史占位值。历史导入将缺项转为确认的占位字符串并标记来源行待清洗。

`FINISHED_RECEIPT` 没有首版日常创建入口，但其单据和明细结构与其他类型一致，供历史 Excel 中的成品入库量建立成品库存。未来工艺卡和成品入库功能应在同一迁移中新增其表及 `inventory_document_line` 的明确外键，不提前放置无外键的占位 UUID 字段。

#### 导入来源表

| 表 | 字段 | 约束与索引 |
|---|---|---|
| `inventory_import_batch` | `id UUID PK`；`source_fingerprint CHAR(64) NOT NULL`；`raw_workbook_sha256 CHAR(64) NOT NULL`；`finished_workbook_sha256 CHAR(64) NOT NULL`；`importer_version VARCHAR(64) NOT NULL`；`reconciliation_report JSONB NOT NULL`；`imported_at TIMESTAMPTZ NOT NULL`；审计字段 | `source_fingerprint` 唯一，取两份工作簿哈希的确定性组合，因此更换导入器版本也不能重复导入同一份源数据；dry-run 不创建本表记录。 |
| `legacy_import_row` | `id UUID PK`；`import_batch_id UUID NOT NULL FK inventory_import_batch`；`workbook_kind legacy_workbook_kind NOT NULL`；`workbook_name VARCHAR(255) NOT NULL`；`worksheet_name VARCHAR(255) NOT NULL`；`source_row_number INTEGER NOT NULL`；`raw_cells JSONB NOT NULL`；`source_balance_snapshot JSONB NOT NULL`；`requires_cleanup BOOLEAN NOT NULL DEFAULT false`；审计字段 | `source_row_number > 0`；`UNIQUE(import_batch_id, workbook_kind, worksheet_name, source_row_number)`。该唯一约束同时提供来源定位索引；每个实际 Excel 行均有一条记录，即使它不产生业务库存变动。 |

`raw_cells` 保存原始单元格，`source_balance_snapshot` 只保存 Excel 中的静态库存列供对账；两者都不参与系统余额计算。导入批次回滚由受控命令按依赖反向删除本批次创建的日记账、单据、来源行和批次记录完成，不开放 HTTP 接口。

#### 库存日记账与余额视图

| 表 / 视图 | 字段 | 约束与索引 |
|---|---|---|
| `inventory_ledger_entry` | `id UUID PK`；`ledger_kind inventory_ledger_kind NOT NULL`；`movement_type inventory_movement_type NOT NULL`；`business_date DATE NOT NULL`；`processing_unit_id UUID NOT NULL FK processing_unit`；`document_line_id UUID NULL FK inventory_document_line`；`legacy_import_row_id UUID NULL FK legacy_import_row`；`import_batch_id UUID NULL FK inventory_import_batch`；`item_name VARCHAR(255) NOT NULL`；`item_code VARCHAR(255) NULL`；`wool_content VARCHAR(255) NOT NULL`；`color_code VARCHAR(255) NULL`；`dye_lot_no VARCHAR(255) NULL`；`rolls_delta INTEGER NOT NULL`；`meters_delta NUMERIC(18,3) NOT NULL DEFAULT 0`；`reason TEXT NULL`；审计字段 | `UNIQUE(document_line_id)`；`MIGRATION_RECONCILIATION_OPENING` 必须没有 `document_line_id`、必须有关联 `import_batch_id`，其他变动必须关联一条明细。原材料账要求 `item_code` 非空、颜色/缸号为空且 `meters_delta = 0`；成品账要求颜色和缸号非空、`item_code` 为空。建立来料余额键索引 `(processing_unit_id, item_name, item_code, wool_content, business_date)` 的 `RAW` 部分索引，以及成品余额键 `(processing_unit_id, item_name, wool_content, color_code, dye_lot_no, business_date)` 的 `FINISHED` 部分索引。 |
| `raw_inventory_balance_v` | 按 `processing_unit_id + item_name + item_code + wool_content` 分组；输出 `SUM(rolls_delta) AS rolls_balance` | 只聚合 `deleted_at IS NULL` 的日记账及其关联未删除单据，以及无单据的迁移对账期初；视图不隐藏负数，服务层、导入对账和测试必须将任何负值视为不变量被破坏。 |
| `finished_inventory_balance_v` | 按 `processing_unit_id + item_name + wool_content + color_code + dye_lot_no` 分组；输出 `SUM(rolls_delta)`、`SUM(meters_delta)` | 与来料余额视图使用相同的日记账和单据有效性规则；两个余额都必须非负。 |

日常明细中的数量始终是正数，服务层根据单据类型写入带符号的 `rolls_delta` / `meters_delta`：来料入库和成品入库为正，坯布退走和成品出货为负。每条明细恰好对应一条日记账；同一历史来源行同时包含成品入库与出库时，创建两个单据明细和两条日记账，并令它们的 `legacy_import_row_id` 指向同一来源行。

单据编辑在一个事务内同步更新其明细和关联日记账快照；软删除仅将 `inventory_document.deleted_at` 设为当前 UTC 时间，余额视图因而自动排除整张单据，恢复时设回 `NULL` 后自动重新纳入。迁移对账期初没有单据明细，不能从日常编辑、删除或恢复流程访问。

#### 外键与数据生命周期

- `inventory_document` 到加工单位、收货单位使用 `ON DELETE RESTRICT`，防止主数据物理删除破坏历史。
- `inventory_document_line` 到单据头使用 `ON DELETE CASCADE`，仅用于受控导入回滚中的物理删除；日常操作不物理删除单据头。
- 日记账到单据明细、历史来源行和导入批次均使用 `ON DELETE RESTRICT`；回滚按“日记账 -> 单据/来源行 -> 批次”的反向顺序执行，避免隐式级联误删审计数据。
- 历史来源行到导入批次使用 `ON DELETE RESTRICT`。只有导入器的失败回滚或经人工确认的重导流程可以执行上述物理删除。

#### 实现约束

Alembic 迁移应先创建四个枚举，再依次创建主数据、单据、导入来源、日记账和余额视图；降级时按相反顺序删除。`models/inventory.py` 只声明表和关系，余额视图通过仓储层使用 `select` / 聚合查询访问，不映射为可写 SQLModel。非负余额、单位是否已停用、跨表单据类型约束和库存并发校验均属于同一事务内的服务层规则，不能仅依赖数据库 `CHECK`。

### 3.3 单据、历史来源与库存日记账

新建业务单据使用单据头和多条明细：

| 单据类型 | 单据头 | 明细与产生的库存变动 |
|---|---|---|
| 来料入库 | 日期、加工单位、单号、备注 | 品名、品号、含毛量、入库匹数；写入来料 `RAW_RECEIPT` 正变动 |
| 坯布退走 | 日期、加工单位、单号、备注 | 同来料识别字段、退走匹数；写入来料 `RAW_RETURN` 负变动 |
| 成品出货 | 日期、加工单位、收货单位、出库单号、备注 | 品名、含毛量、颜色/色号、缸号、出库匹数、出库米数；写入成品 `FINISHED_SHIPMENT` 双负变动 |

每一条业务明细对应不可直接编辑的库存日记账变动。日记账保留：所属台账、变动类型、原因、库存识别维度、匹数增减、米数增减、所属业务明细、创建时间。历史导入的成品入库会写入 `FINISHED_RECEIPT` 正变动；其日常页面及与工艺卡的关联不在本期实现。

历史导入另保存 `LegacyImportRow`：原工作簿、工作表、行号、原始单元格数据、原库存快照和“历史待清洗”标记。每行至少有一个 `LegacyImportRow`；一行同时有成品入库和出库时，会生成两条关联同一来源行的库存日记账变动。历史记录可以在业务页面编辑或软删除其归一化后的业务字段和变动，但原始来源快照保持不变以便审计。

### 3.4 库存识别键

| 台账 | 归并键 | 余额 |
|---|---|---|
| 来料 | 加工单位 + 品名 + 品号 + 含毛量 | 匹数 |
| 成品 | 加工单位 + 品名 + 含毛量 + 颜色/色号 + 缸号 | 匹数、米数 |

键字段在写入前执行确定性规范化（去首尾空白、合并连续空白）；`全毛`等业务文本保留为文本。新业务不得使用“未填写品号”“未填写含毛量”“未分缸”这类遗留占位值；历史导入仅在源单元格缺失时使用它们并标记待清洗。

日期、单号、出库单号、收货单位和备注不参与归并。坯布数量为正整数匹；成品出货匹数为正整数、米数为正 Decimal，二者必须同时输入。

### 3.5 软删除、编辑和非负不变量

- 软删除单据或历史行后，其日记账变动不再参与余额；记录和来源定位保留。
- 恢复、编辑和删除在一个数据库事务内处理。服务先按库存键聚合本次变动，再以“排除旧版本后的余额 + 新版本聚合量”校验，任一结果小于零即拒绝整个请求。
- 日常业务变动没有草稿、审批或撤销状态；保存即生效。
- “迁移对账期初”只由首次导入器创建，带来源、原因和库存键，不出现在日常编辑/删除入口，也不等同于未来的库存调整单。

## 4. 首次 Excel 导入

导入器是受控命令，不是 HTTP 页面。它在尚无库存模块数据的数据库上运行一次，并记录导入批次指纹，重复运行默认拒绝；既有用户和平台数据不受影响。

1. 读取两份工作簿及每个工作表，逐行保存 `LegacyImportRow`。
2. 根据表头差异映射坯布两种列布局；将 `*退走` 加工单位映射为原加工单位加 `RAW_RETURN`；将成品行的入库、出库列分别映射为相应的日记账变动。
3. 对缺失的品号、含毛量或缸号使用确认的遗留占位值并设置待清洗标记。
4. 按原表行序回放变动。某库存键第一次将变动后的余额降到零以下时，在该变动之前写入最小必要数量的 `MIGRATION_RECONCILIATION_OPENING` 正变动，然后再写入原始历史变动。
5. 保存每行的 Excel 库存快照；系统余额永远以日记账聚合为准。
6. 输出按库存键的导入对账报告：导入行数、来源行数、待清洗行数、迁移对账期初数量、最终匹数/米数和与原快照的差异。差异必须由人工确认后才能视为导入完成。

导入产生的历史空单号或同类型重复单号可保留并标记历史；新建单据始终要求手工单号且在自身类型内唯一。

## 5. API 与错误流

路由以 `/api/v1/inventory` 为前缀，均要求当前登录用户；首版不增加业务角色。

- 主数据：加工单位、收货单位的列表、新建、更新、停用接口。
- 单据：三类单据的分页列表、详情、新建、更新、软删除、恢复接口；查询参数至少支持日期区间、加工单位、单号和历史/已删除状态，成品再支持收货单位。
- 库存：来料、成品余额聚合列表及按库存键查询关联日记账/业务明细的接口。
- 联想：按字段和台账返回已保存的去重值；输入仍可创建新的规格值。

服务层将以下业务失败抛为语义化应用错误：无效/已停用主数据、空或重复的新单号、遗留占位值用于新单据、数量规则错误、库存不足、不可编辑的迁移对账记录、对象不存在。它们沿用全局错误处理，前端按 `detail` 展示，并保留响应的 `request_id`。

后端 schema 变更后必须用现有生成脚本刷新 OpenAPI 客户端；不得手改 `frontend/src/client/**`。

## 6. 前端交互与页面

| 页面组 | 路由和界面 | 核心交互 |
|---|---|---|
| 主数据 | `/inventory/masters`，加工单位/收货单位页签 | 表格、创建/编辑、停用；历史被引用数据仍可检索 |
| 坯布台账 | `/inventory/raw`，来料入库/坯布退走页签 | 单据列表筛选；多明细表单；编辑、软删除、恢复；规格联想 |
| 成品出货 | `/inventory/shipments` | 单据列表筛选；多明细出货表单；匹数和米数双字段校验；编辑、软删除、恢复 |
| 库存 | `/inventory/balances`，来料/成品页签 | 余额汇总、按库存键筛选、抽屉查看关联明细和历史来源标识 |

每个页面均明确呈现 loading、empty、error 和 mutation-pending 状态。余额列是只读显示；表单不提供直接修改库存的控件。写成功后使对应单据列表、两类库存余额、联想值和受影响明细查询失效并重新获取。

## 7. 风险、兼容与回滚

- 首次导入是唯一会创建迁移对账期初的路径；必须在事务和导入批次记录下完成。失败时回滚整个批次，不能留半导入数据。
- 新增的 router、模型、Alembic revision、OpenAPI client 和 feature routes 是本功能边界；不修改或迁移 `Item`，保留现有 `/api/v1/items/*` 行为。
- 若导入对账不能确认，回滚本次导入批次及其生成的日记账/来源行，修正映射后重新执行受控命令；日常页面不提供此能力。
- 当前是单人使用。若未来改为多人并发录单，需要在库存键上加入更强的数据库锁或余额投影锁；本期不引入审批或并发协作流程。

## 8. 文档与规格结论

本功能会使用现有 Ant Design 6 和模块边界规范；现有规格已经记录该通用约束。本次没有新的跨任务通用规则需要写入 `.trellis/spec/**`，完成后只需在任务和必要的运行说明中记录首次导入命令与对账结果。
