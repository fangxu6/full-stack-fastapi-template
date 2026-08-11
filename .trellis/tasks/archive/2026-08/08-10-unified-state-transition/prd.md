# 统一状态方案

## Goal

为具有工作流复杂度的 DDD 领域模块建立一套前向生效的状态迁移设计契约：状态和事件保持领域本地化，但状态迁移矩阵的表达、命名、并发/幂等说明、审计和测试要求保持一致。

本任务的用户价值是让后续开发任务能够明确描述有限状态的允许迁移和副作用，避免把不同领域塞进一张全局状态表，也避免在实现阶段遗漏非法迁移、恢复、租约或并发边界。

## Confirmed Facts

- `docs/state-machine-unified-transition-design.md` 当前已存在但未跟踪，内容仍是此前讨论稿；本任务需要在保留有效内容的基础上核对并完善它，不得覆盖用户已有内容。
- `SchedulerRun` 已有持久化状态与集中生命周期边界：`backend/app/modules/scheduler/run_lifecycle.py` 负责运行状态、租约、终态和清理写入；`docs/adr/0012-concentrate-scheduler-run-lifecycle-state.md` 记录了这一决定。
- 库存纠错是已完成的真实多对象工作流：申请、工作项和 Attempt 各有独立状态，设计中已包含一张无统一名称的申请状态迁移表，见 `.trellis/tasks/archive/2026-08/08-04-inventory-exception-correction/design.md`。
- 用户已决定本任务回填 scheduler、库存纠错、Email Outbox 和库存日报投递的现有工作流状态迁移矩阵；回填是设计文档工作，不改变这些模块的运行时代码。
- `backend/app/models/inventory.py`、`backend/app/models/scheduler.py` 和 `backend/app/models/email.py` 已使用领域内 `StrEnum` 与 PostgreSQL enum 保存有限状态；数据库规则已规定持久化业务状态使用命名 `StrEnum`，而不是把开放分类或真正二元事实误建模为状态。
- `.trellis/spec/backend/directory-structure.md` 已规定多表工作流、状态迁移或持久化异步行为应拥有模块边界；`.trellis/spec/guides/code-reuse-thinking-guide.md` 规定领域工作流组件应留在领域目录。
- `.trellis/spec/backend/async-task-guidelines.md` 的调度生命周期段存在已知陈旧的 `finish_run(...)` 说明，且由活跃任务 `08-07-correct-scheduler-lifecycle-spec` 负责修复。本任务不得同时修改该文件，以免抢占其所有权。
- `08-03-business-workflow-platform` 仍明确禁止在没有第二个被证实使用者前建设通用工作流运行时、通用审批表或工作项平台。

## Requirements

### R1. 方案文档

核对并完善 `docs/state-machine-unified-transition-design.md`，记录：

- 当前项目的状态机/生命周期盘点与代码锚点。
- scheduler、库存纠错、Email Outbox 和库存日报投递按聚合拆分的状态迁移矩阵；每个矩阵都使用 R3 的统一名称和固定列，且以当前代码行为为准。
- 该文档是四类既有工作流矩阵的唯一规范载体；已归档 Trellis 设计和 ADR 继续作为历史事实来源，不复制或改写其中的矩阵。
- “领域独立状态 + 共享最小迁移机制”方案。
- 不新增通用工作流表、不引入第三方状态机库、不建立全局状态矩阵的理由。
- 状态迁移矩阵不需要新增数据库表的原因，以及何时才需要动态工作流表。
- 局部矩阵如何避免随领域增加而失去可读性。
- 渐进式采用顺序、风险、非目标和后续任务边界。

### R2. DDD 工作流状态迁移规则

在 `.trellis/spec` 中新增或扩展后端规则，使其成为后续任务的可执行设计约束：

- `enum` 与状态迁移矩阵承担不同职责：`enum` 定义字段可取的封闭值集合；状态迁移矩阵定义工作流状态在事件驱动下允许如何随时间变化。状态机的状态通常仍应由领域本地的 `StrEnum` 表示和持久化，矩阵不替代枚举。
- 不依赖当前值来约束后续行为的封闭分类只使用 `enum`，不要求矩阵，例如类别、触发来源、策略、角色或错误分类。`EmailOutboxKind` 与 `SchedulerRunTrigger` 是本项目的代表性示例。
- 当枚举值表示聚合生命周期阶段，且当前值会决定允许的下一步、终态、重试/恢复、租约、权限、跨实体副作用或并发处理时，它是工作流状态；符合本规则的 DDD 工作流模块必须提供矩阵。`EmailOutboxStatus` 与 `SchedulerRunStatus` 是本项目的代表性示例。
- 只有简单状态字段且不存在多步业务流程、恢复/重试、并发边界或跨实体协调时，不强制建立矩阵；若该字段演化为工作流状态，必须在同一设计变更中补充矩阵。
- 当 `modules/*` 内的领域设计包含有限业务状态、状态改变事件、跨实体工作流、租约、重试、恢复或终态语义时，设计文档必须包含状态迁移矩阵。
- 矩阵描述结构性迁移关系；业务权限、时间戳/版本、数据完整性等前置条件不能被矩阵替代。
- 多表状态变化必须仍由领域服务在同一事务内协调；共享机制不得成为通用工作流运行时或跨领域注册中心。
- 已持久化状态继续遵守 `StrEnum`、PostgreSQL enum、迁移、注释和 API 契约规则。
- 状态迁移测试必须覆盖合法迁移、非法迁移、终态、恢复或重试（如适用）、幂等与并发边界。

### R3. 状态迁移矩阵命名规范

规则文件必须定义如下规范，并在方案文档中解释：

| 对象 | 规范 |
| --- | --- |
| 设计文档章节 | `## 状态迁移矩阵（State Transition Matrix）` |
| 单个矩阵标题 | `<领域>.<聚合> 状态迁移矩阵`，例如 `inventory.correction_request 状态迁移矩阵` |
| 表格列 | `当前状态`、`事件`、`目标状态`、`前置条件`、`副作用`、`幂等/并发语义` |
| 状态枚举 | `<Aggregate>State`；已存在且语义准确的 `<Aggregate>Status` 不要求改名 |
| 事件枚举 | `<Aggregate>Event`，取值使用领域动词，例如 `APPROVE`、`CLAIM`、`DELIVER` |
| 可选代码规则常量 | `<AGGREGATE>_TRANSITIONS`，仅在矩阵确实作为代码校验来源时定义，并保留在领域模块内 |
| 禁止形式 | `ALL_TRANSITIONS`、跨领域公共状态枚举、可动态执行任意领域回调的全局注册中心 |

### R4. 规则文件接入

规划应确定并在实施时更新最小相关文件。当前预期为：

- 新增一个后端状态迁移规则文件，并从 `.trellis/spec/backend/index.md` 链接。
- 在 `.trellis/spec/backend/database-guidelines.md` 的持久化业务状态场景增加到新规则的交叉引用，而不重复数据库枚举规则。
- 在 `.trellis/spec/backend/directory-structure.md` 的模块升级说明中增加“工作流设计矩阵”要求。
- 从 `docs/README.md` 链接新的方案文档。

具体文件和正文需在设计阶段复核，避免与活跃任务的规范修改范围冲突。

## Acceptance Criteria

- [ ] `docs/state-machine-unified-transition-design.md` 存在，并完整说明 R1 的范围和结论。
- [ ] 方案文档回填 scheduler、库存纠错、Email Outbox 和库存日报投递的状态迁移矩阵；多聚合领域按其聚合分别成表，不把不同行为压缩为一张全局表。
- [ ] 四类回填矩阵只在统一方案文档维护；归档 Trellis 任务和 ADR 不被改写或复制矩阵。
- [ ] `.trellis/spec` 明确区分领域局部状态迁移契约与通用工作流运行时。
- [ ] `.trellis/spec` 明确 `enum` 是封闭取值集合、矩阵是工作流状态的允许迁移关系；普通分类枚举不要求矩阵。
- [ ] 新规则要求符合触发条件的 DDD 工作流模块在设计阶段提供状态迁移矩阵，并定义 R3 的章节、矩阵、状态、事件和可选代码常量命名。
- [ ] 新规则定义矩阵的必填列以及前置条件、跨表副作用、事务、幂等、并发和测试边界。
- [ ] 现有 `StrEnum` / PostgreSQL enum 规则与新状态迁移规则互相引用而不重复或矛盾。
- [ ] 不修改应用业务代码、数据库 schema、Alembic revision、前端 API 或生成客户端。
- [ ] 不修改 `async-task-guidelines.md`，并在交叉引用或设计说明中保留其由 `08-07-correct-scheduler-lifecycle-spec` 所有的事实。
- [ ] 文档链接、Markdown 格式和 Trellis 规则索引通过项目提供的文档/规范检查。

## Out Of Scope

- 通用工作流运行时、审批引擎、动态状态配置、工作流数据库表、待办或通用工作项 UI。
- 引入第三方状态机库或 Temporal。
- 将现有状态字段、布尔字段或领域服务重构为矩阵驱动实现；本任务只回填既有运行时行为的设计矩阵。
- 为了复制矩阵而改写已归档 Trellis 任务或 ADR。
- 修改调度器运行生命周期、库存纠错、Outbox 或日报的运行时代码。
- 修复 `async-task-guidelines.md` 中的陈旧 scheduler 说明；该工作由 `08-07-correct-scheduler-lifecycle-spec` 拥有。

## Scope Decision

本规则对后续新建或实质修改的 DDD 工作流模块前向生效；同时，本任务必须回填 scheduler、库存纠错、Email Outbox 和库存日报投递的现有设计矩阵。回填范围仅限基于当前代码的文档矩阵、统一方案文档和 `.trellis/spec` 规则，不得借机改变运行时状态处理或引入通用工作流平台。四类矩阵集中维护在 `docs/state-machine-unified-transition-design.md`；归档 Trellis 任务和 ADR 只作为事实来源，不在本任务改写或复制矩阵。
