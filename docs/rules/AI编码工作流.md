# AI 编码工作流（本项目）

这份流程把最近一次 `/last30days AI coding` 的结论落到本仓库：AI coding 的有效形态不是“让模型一次性写完”，而是用短 leash、明确上下文、可验证小步和复核门禁，把 Agent 当成受控的工程协作者。

适用范围：

- `backend/app/**`：FastAPI、SQLModel、服务层、错误契约、日志。
- `frontend/src/**`：React、TanStack Router、React Query、OpenAPI client、页面与权限。
- `.trellis/**`、`docs/specs/**`、`docs/llm-wiki/**`：任务、规范、可复用知识。

## 1. 默认原则

1. **短 leash。** 每次只让 AI 做一个可验证切片：一个 bug、一个页面、一个 API contract、一个测试补齐点。不要用“大范围重构一下”“优化整个前端”这类指令直接开工。
2. **先读真实上下文。** 代码事实优先于记忆和模板。先直接读取已知入口，再按需要用窄范围 `rg` 核验调用链、边界、测试和影响面。
3. **Trellis 管生命周期。** 复杂任务走 `.trellis/workflow.md`：需求、设计、实现计划、执行、检查、规范更新。小任务可以 inline，但也要保留完成标准和验证结果。
4. **规范是门禁，不是建议。** Backend 读 `.trellis/spec/backend/index.md`，Frontend 读 `.trellis/spec/frontend/index.md`，跨层改动读 `.trellis/spec/guides/index.md`。
5. **AI 输出必须被验证。** 任何代码改动至少跑与风险匹配的 lint、type-check、test 或 build。不要把“模型看起来合理”当成完成。
6. **长期知识落文件。** 重复踩坑、跨层契约、审查发现要写回 `.trellis/spec/**`、`docs/specs/**` 或 `docs/llm-wiki/**`，不要只留在聊天里。

## 2. 任务分流

| 请求类型 | 推荐模式 | 是否建 Trellis task | 最小交付 |
| --- | --- | --- | --- |
| 解释代码、查调用链 | 只读分析 | 否 | 文件路径、调用链、结论和不确定性 |
| 小修 bug / 小文档 | Codex inline | 可选 | 小 diff + 针对性验证 |
| 新 API / 新页面 / 跨层契约 | Trellis planning | 是 | `prd.md`、必要时 `design.md`、`implement.md`、验证记录 |
| 大重构 / 多交付 | Trellis parent + child tasks | 是 | 子任务拆分、每个子任务独立验收 |
| Review | review stance | 否 | 真实风险优先，按严重程度列问题 |
| 调研外部工具/库 | research artifact | 视情况 | 写入 `research/`、`docs/llm-wiki/` 或 `docs/rules/` |

## 3. 每次开工的上下文包

### 后端改动

先读：

```text
AGENTS.md
.trellis/spec/backend/index.md
.trellis/spec/backend/directory-structure.md
.trellis/spec/backend/database-guidelines.md        # 改 models / schemas / migrations 时
.trellis/spec/backend/error-handling.md            # 改 API / service 错误行为时
.trellis/spec/backend/logging-guidelines.md         # 改请求链路或异常记录时
.trellis/spec/backend/quality-guidelines.md
```

常用验证：

```powershell
cd backend
uv run pytest tests/
uv run mypy app
uv run ty check app
ruff check app tests
```

跨层 API 变更后：

```powershell
bash ./scripts/generate-client.sh
```

### 前端改动

先读：

```text
AGENTS.md
.trellis/spec/frontend/index.md
.trellis/spec/frontend/directory-structure.md
.trellis/spec/frontend/component-guidelines.md
.trellis/spec/frontend/type-safety.md
.trellis/spec/frontend/quality-guidelines.md
```

如果涉及路由、菜单、权限、页面移动，再读：

```text
.trellis/spec/frontend/route-permission-navigation-contract.md
.trellis/spec/frontend/state-management.md
.trellis/spec/frontend/hook-guidelines.md
```

可写 lint/fix（会自动改文件，运行后必须复核 `git diff`）：

```powershell
cd frontend
bun run lint
```

只读 Review gate：

```powershell
cd frontend
bunx biome ci --no-errors-on-unmatched --files-ignore-unknown=true ./
bun run build
bunx playwright test
```

### 跨层改动

先读：

```text
.trellis/spec/guides/index.md
.trellis/spec/guides/cross-layer-thinking-guide.md
.trellis/spec/backend/index.md
.trellis/spec/frontend/index.md
```

必须检查：

- 后端 response/error shape 是否改变。
- `detail` + `request_id` 是否仍保留。
- OpenAPI client 是否需要重新生成。
- Frontend route、menu、permission、page placement 是否同步。
- 是否需要新增/更新 `docs/specs/<feature>/`。

## 4. 短 leash 执行循环

每个实现切片按这个循环走：

1. **说清切片。** 用一句话写清这一步只改什么，不改什么。
2. **定位事实。** 先读取当前入口，再用窄范围 `rg` 找调用链、测试和相邻模式。
3. **列检查点。** 写出本切片的验收条件和要跑的命令。
4. **小步编辑。** 一次只改一组相关文件，避免顺手重构。
5. **立即验证。** 跑最小相关检查；失败先修，再继续下一切片。
6. **复核 diff。** 看是否有生成文件误改、无关格式化、厚 route、手写 client、错误契约破坏。
7. **记录学习。** 如果出现新规则或坑，写回 Trellis spec 或相关 docs。

推荐提示词：

```text
目标：修复/实现 <具体目标>。
上下文：请先读 AGENTS.md、相关 .trellis/spec，并用直接读取和窄范围 `rg` 找真实调用链。
约束：只做 <范围>；不要改 <排除范围>；保持后端 detail + request_id；不要手改 frontend/src/client/**。
完成标准：列出计划，执行小步修改，跑 <命令>，最后说明验证结果和剩余风险。
```

## 5. 本仓库的“不要让 AI 乱跑”清单

- 不要让 AI 在没有读 `.trellis/spec/**` 的情况下修改 `backend/app/**` 或 `frontend/src/**`。
- 不要让 AI 把业务页面重新塞回 `frontend/src/routes/**`；routes 应保持 thin。
- 不要让 AI 手写或手改 `frontend/src/client/**`；后端 contract 变更后重新生成 client。
- 不要让 AI 绕过统一错误契约；后端错误响应要保留 `detail` 和 `request_id`。
- 不要让 AI 因为“代码重复”过早把页面私有逻辑升到 `shared/*`。
- 不要让 AI 一次性重构 backend `crud`、`services`、`modules` 边界；先写设计和回滚点。
- 不要让 AI 把 HN/Reddit 上的趋势直接当成 repo 规则；外部信号只能转成本仓库可验证的 guardrail。
- 不要让 AI 提交无关脏文件；提交前先按 `.trellis/workflow.md` 的 Phase 3.4 分类 dirty state。

## 6. Review 门禁

让 AI review 时，用这个固定重点：

```text
请按 code-review stance 审查当前 diff：
- 先列 bug、行为回归、安全风险、遗漏测试，按严重程度排序；
- 检查是否违反 .trellis/spec/backend 或 .trellis/spec/frontend；
- 检查跨层契约：OpenAPI client、request_id、route/menu/permission；
- 检查是否有无关格式化、生成文件误改、手写 client；
- 最后给出验证命令是否足够，不要把总结放在问题前面。
```

后端重点：

- API 错误是否仍有 `request_id`。
- route 是否过厚，业务逻辑是否应在 service。
- SQLModel schema / model / Alembic 是否一致。
- 日志是否能用 request_id 串起来。

前端重点：

- route 是否 thin。
- page / feature / platform / shared 放置是否正确。
- React Query、auth、permission、navigation 是否同步。
- 类型是否来自 generated client / Zod，而不是散落的临时类型。

## 7. 推荐的 AI 协作节奏

### 小 bug

```text
1. 复现或定位失败点。
2. 找相邻测试。
3. 做最小修复。
4. 跑相关测试。
5. 如果暴露长期规则，更新 spec。
```

### 新功能

```text
1. 建 Trellis task。
2. 写 PRD，复杂任务补 design.md 和 implement.md。
3. 读 backend/frontend/guides specs。
4. 后端先定 contract 和测试。
5. 生成 frontend client。
6. 前端接入页面、权限、导航。
7. 跑后端测试、前端 lint/build、必要时 Playwright。
8. 更新 spec / llm-wiki 中可复用知识。
```

### UI 改动

```text
1. 读 frontend spec。
2. 明确目标用户和工作流。
3. 保持页面结构符合 app / platform / features / shared / routes 分层。
4. 使用现有组件和 lucide icons。
5. 启动前端或用 Playwright 截图验证布局。
```

### 外部技术选型

```text
1. 用官方文档或 Context7 查当前 API。
2. 把关键发现写到 task research 或 docs。
3. 做最小 spike，不直接大面积替换。
4. 再决定是否进入实现。
```

## 8. 常用命令索引

```powershell
# 查看 Trellis 包/层规范
python ./.trellis/scripts/get_context.py --mode packages

# 后端
cd backend
uv sync
uv run pytest tests/
uv run mypy app
uv run ty check app
ruff check app tests

# 前端
cd frontend
bun install
bun run lint
bun run build
bunx playwright test

# 全栈
docker compose watch
bash ./scripts/generate-client.sh
bash ./scripts/test.sh

# 提交前
git status --short
git diff --check
```

## 9. 何时更新这份流程

出现以下情况时，更新本文件或对应 `.trellis/spec/**`：

- AI 在同一类问题上重复犯错。
- Review 发现某类遗漏测试或跨层回归。
- 引入新的 Codex hooks、subagents、skills 或 MCP 工具。
- 前端/后端目录边界发生正式调整。
- `/last30days` 或其他外部调研发现的趋势被验证为本仓库有效实践。
