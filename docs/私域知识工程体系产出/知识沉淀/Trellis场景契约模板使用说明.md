## Trellis 场景契约模板使用说明

### 关键结论

- 场景契约模板位于 `.trellis/spec/templates/scenario-contract-template.md`，用于沉淀“只在特定触发条件下必须读取”的高风险规则。
- 它不是通用开发规范，也不是任务 PRD；它更像一份可执行的防回归契约，要求后续 AI 在遇到对应场景时按固定入口、固定校验方式工作。
- 当前仓库已有一个落地示例：`.trellis/spec/frontend/route-permission-navigation-contract.md`，用于约束前端路由、菜单、权限、页面放置之间的一致性。

### 模板解决什么问题

普通规范适合记录长期通用规则，例如后端异常格式、前端目录分层、测试命令等。

场景契约适合记录“范围更窄、风险更高、跨文件更容易漏同步”的规则。例如：

- OpenAPI schema 变化后，必须重新生成前端 client。
- 统一错误结构变更后，必须验证 `request_id`、日志与 API 响应。
- 登录、当前用户、退出逻辑变化后，必须同步鉴权状态与跳转行为。
- 前端新增页面、路由、菜单、权限时，必须同步 guard、menu config、permission helper。
- 批量导入导出、批量修改、跨层数据流等高风险场景，需要明确成功、失败、权限、陈旧配置的验证矩阵。

这类规则如果只写在聊天记录或泛泛的最佳实践里，后续 AI 很容易只改其中一个文件，造成隐性回归。场景契约的作用就是把触发条件、涉及文件、行为不变量、验证方式和反例固定下来。

### 什么时候需要新增场景契约

满足以下任一条件，建议新增或补充场景契约：

- 一个改动横跨 backend、frontend、生成代码、配置或文档。
- 一个规则过去已经出现过漏改、漏测或重复返工。
- 一个行为依赖多个入口保持一致，例如路由可访问性和菜单可见性。
- 一个文件看起来能单独改，但真实正确性依赖另一个文件或命令。
- 一个错误不是语法错误，而是“业务路径仍能跑但语义已经错了”。

不建议为普通、低风险、单文件规则新增场景契约。那类内容应放在对应层的普通规范里，例如 `.trellis/spec/backend/*`、`.trellis/spec/frontend/*` 或 `.trellis/spec/guides/*`。

### 如何填写模板

#### 1. Scope / Trigger

写清楚什么时候必须读取这份契约。

建议包含：

- 触发条件：例如“新增 protected route”“修改 OpenAPI schema”“调整权限判断入口”。
- 主文件：列出真正定义契约的文件，而不是泛泛写目录。
- 不包含范围：说明哪些相似场景不归这份契约管，避免未来误套。

#### 2. Signatures / Interfaces

列出契约入口。

可以是：

- FastAPI route、service、schema。
- React route、page module、hook、permission helper。
- 生成文件、脚本、配置项。
- 命令入口，例如 `scripts/generate-client.sh`。

这一段的目的不是解释实现细节，而是告诉后续 AI：哪些名字变了，就代表契约也可能变了。

#### 3. Contracts

写不可回归的不变量。

推荐写法：

- 哪一层拥有哪部分职责。
- 哪些文件必须同步。
- 哪些行为必须保持一致。
- 哪些捷径明确禁止。

例如前端路由场景中，契约要求：

- `routes/*` 保持薄路由入口。
- 页面实现放到 `platform/*/pages` 或 `features/*/pages`。
- 路由访问由 `app/router/guards.ts` 控制。
- 菜单可见性由 `app/navigation/*` 和 `shared/permissions/*` 控制。

#### 4. Validation & Error Matrix

用表格写清不同条件下的期望行为和验证方式。

至少覆盖：

- 正常路径。
- 非法输入。
- 未登录或无权限。
- 生成代码、配置、菜单、文档等陈旧状态。

验证方式要尽量具体，能写命令就写命令，能写测试名就写测试名。不要只写“人工确认”。

#### 5. Good / Base / Bad Cases

用真实仓库例子说明边界。

- Good：当前项目里已经采用的推荐做法。
- Base：短期可接受但不完美的最低方案。
- Bad：这份契约明确防止的错误做法。

这一段对 AI 特别有用，因为它能把抽象规则变成可比对的实现模式。

#### 6. Tests Required

列出该场景完成前必须执行的验证。

可以按层拆分：

- Backend：unit、API、service、migration、schema 测试。
- Frontend：lint、build、component、Playwright、路由跳转检查。
- Cross-layer：OpenAPI client 生成、菜单与路由一致性、数据往返验证。

#### 7. Wrong vs Correct

把常见错误和正确做法并排写出来。

这一段要具体，不要写空泛口号。例如“不要把权限判断散落在页面组件里”，比“注意权限一致性”更有执行价值。

### 如何落到当前项目

新增场景契约时，建议按以下步骤执行：

1. 复制 `.trellis/spec/templates/scenario-contract-template.md`。
2. 放到最接近触发场景的目录，例如：
   - 前端场景：`.trellis/spec/frontend/{contract-name}-contract.md`
   - 后端场景：`.trellis/spec/backend/{contract-name}-contract.md`
   - 跨层场景：可放在 `.trellis/spec/guides/`，或根据主要拥有层放置并在另一个层索引中引用。
3. 用当前仓库真实文件和命令替换占位符。
4. 在对应层的 `index.md` 中增加链接。
5. 如果是高风险触发规则，也要同步 `.trellis/spec/index.md` 的 “High-Risk Trigger Routing” 或 “Scenario Contract Standard”。
6. 在 `.trellis/spec/log.md` 追加变更记录。
7. 运行基础校验：
   - Markdown 链接可打开。
   - 路径没有引用不存在的文件。
   - 没有保留模板里的占位文本。
   - 相关 lint、test、build 命令按契约要求执行。

### 当前示例怎么读

`.trellis/spec/frontend/route-permission-navigation-contract.md` 是现有示例。

它的触发条件是前端页面、受保护路由、菜单项、权限入口、页面位置变化。它把相关文件集中列出来，并明确：

- route 文件只做入口。
- 页面实现不能长期堆在 `routes/*.tsx`。
- admin 路由必须通过 `requireSuperuser`。
- 菜单可见性必须和 `canAccessAdmin` 等权限入口保持一致。
- `bun run lint` 和必要的 `bun run build` 是此类改动的基础验证。

后续如果要新增类似“OpenAPI client 生成契约”或“统一错误响应契约”，可以照这个文件的粒度写：先定义触发条件，再列入口，再写不可回归规则，最后写验证矩阵和反例。

### 与其他文档的边界

| 文档类型 | 主要用途 | 放置位置 |
| --- | --- | --- |
| 普通开发规范 | 长期通用编码规则 | `.trellis/spec/backend/*`、`.trellis/spec/frontend/*`、`.trellis/spec/guides/*` |
| 场景契约 | 特定高风险场景的防回归规则 | `.trellis/spec/{layer}/*-contract.md` |
| 任务 PRD / 设计 / 实施计划 | 当前任务的需求、方案、执行步骤 | `.trellis/tasks/{task}/` |
| 知识沉淀 | 给人看的中文说明、方法论、项目经验 | `docs/私域知识工程体系产出/知识沉淀/` |
| LLM-Wiki | 可追溯、结构化的 AI 查询知识层 | `docs/llm-wiki/` |

### 维护原则

- 场景契约必须来自当前仓库真实代码、配置或已验证问题，不要从其他项目复制业务规则。
- 契约越具体越好，触发条件不清楚的规则不适合放在场景契约里。
- 新增契约后一定要更新索引，否则后续 AI 不一定会读到。
- 契约不是一次性文档。相关代码路径、命令、目录分层变化后，要同步更新契约。
- 如果一次问题修复暴露出“以后只要遇到这个场景都要这样做”，优先考虑沉淀成场景契约。
