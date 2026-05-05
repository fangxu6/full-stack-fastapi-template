# AI Change Log

Record significant AI-assisted decisions and rationale.

## When To Use

Use this file as the default lightweight decision log for:

- feature work
- bugfixes
- rule or doc refinements
- implementation-level trade-offs

Use `docs/decisions/ADR-xxxx.md` only when the decision is architectural, cross-cutting, long-lived, and expensive to reverse.

In most cases, updating `AI_CHANGELOG.md` alone is enough.

## Template
- Date: YYYY-MM-DD
- Scope: feature or area
- Decision: what changed
- Reason: 变更原因
- Risk: 风险、权衡或后续事项

## Entries
- YYYY-MM-DD: (placeholder)
- Date: 2026-05-05
- Scope: backend import boundary (models vs schemas)
- Decision: Refactored backend imports so `app.models` now exports only ORM/SQLModel entities (`SQLModel`, `User`, `Item`), and all schema types are imported from `app.schemas`/`app.schemas.*`; added the same rule to `docs/rules/项目宪章.md`.
- Reason: 之前 `app.models` 通过聚合导出 schema，导致分层语义混淆（models 与 schemas 职责边界不清）并引入混用导入风格，增加维护和 review 成本。
- Risk: 现有与未来代码若继续沿用旧习惯可能回归混用；需要在后续 review 中持续检查导入边界，确保该规则稳定执行。
- Date: 2026-03-31
- Scope: rules viewer hardening
- Decision: Updated the rules viewer backend so the backend image now includes `docs/rules`, local compose development can sync that directory into the container, and the backend whitelist rejects symlinked Markdown files before exposing any rule document.
- Reason: review 发现当前实现虽然在本地源码目录下可用，但在标准后端镜像中读不到 `docs/rules`，并且 `glob("*.md") + is_file()` 会把 symlink 文件纳入白名单，破坏路径隔离承诺。
- Risk: 当前修复依赖部署产物中继续携带 `docs/rules`；如果未来要扩展到更大的 `docs/**` 范围，仍需要重新审视镜像体积、同步策略和更严格的文件暴露边界。
- Date: 2026-03-31
- Scope: rules viewer mvp
- Decision: Added `docs/specs/rules-viewer-mvp/`, introduced authenticated backend endpoints for `GET /api/v1/docs/rules` and `GET /api/v1/docs/rules/{slug}`, regenerated the OpenAPI client, and added a protected `/rules` page plus sidebar entry so logged-in users can browse `docs/rules/*.md` in the app.
- Reason: 当前仓库已经把 `docs/rules/*.md` 作为项目规则来源之一，但此前只能在仓库文件系统中离线查看；这不利于登录后的使用者直接查阅，也不利于后续把更多 `docs/**` 内容逐步纳入统一的在线文档入口。
- Risk: 当前版本只覆盖 `docs/rules/*.md` 且正文按纯文本展示；如果后续扩展到 `docs/specs/**`、增加 Markdown 渲染或搜索能力，需要重新明确目录白名单、渲染安全和导航结构，避免把 MVP 直接膨胀成通用文档中心。
- Date: 2026-03-31
- Scope: imported rules adaptation
- Decision: Added `docs/specs/imported-rules-adaptation/` and rewrote `docs/rules/数据库规则.md`、`docs/rules/需求宪章.md`、`docs/rules/需求规则.md`、`docs/rules/需求文档编号规范示例.md`、`docs/rules/项目宪章.md` so they now follow the current repository's `docs/specs/<feature>/01~04` workflow and real stack baseline instead of the imported project's MySQL / SQLAlchemy / Ant Design / React Router / `/speckit` / `/Doc/dataDict` assumptions.
- Reason: 这些文档来自另一套文档驱动项目，但长期放在当前仓库的 `docs/rules/` 下，容易被误认为是本仓库的正式规则；而它们实际上与当前仓库的 FastAPI + SQLModel + PostgreSQL + Vite + React 19 + TanStack Router/Query + 生成式 OpenAPI client 流程存在明显冲突。
- Risk: 本批次之外的其他导入文档仍可能保留外来项目假设；如果后续技术栈继续演进，也需要持续同步这些已适配文档与 `AGENTS.md`、`docs/specs/` 和运行时代码。
- Date: 2026-03-31
- Scope: decision record workflow
- Decision: Converted `docs/decisions/ADR-xxxx.md` from an empty placeholder into a reusable ADR template, clarified in `AI_CHANGELOG.md` that normal changes should default here, and updated `AGENTS.md` so major architecture decisions can additionally use ADRs.
- Reason: 仓库里原本只有一个空的 ADR 占位文件，却没有明确说明什么时候该写 ADR、什么时候只更新 `AI_CHANGELOG`，导致贡献者很难判断应该使用哪种记录方式。
- Risk: 如果把普通功能改动都写成 ADR，会让决策记录过于嘈杂；如果真正的架构取舍又不写 ADR，长期原因仍然会丢失。
- Date: 2026-03-31
- Scope: frontend React guidance
- Decision: Updated the repo React guidance so `docs/rules/前端开发规范.md` is the primary source of truth, `react-best-practices` is the first performance reference for regular Vite SPA work, and `vercel-react-best-practices` is only supplemental unless Next.js or server/client boundary concerns are actually in play.
- Reason: 当前仓库是基于 Vite SPA、TanStack Query、TanStack Router 和生成式 OpenAPI client 的前后端分离结构，默认套用偏 Next.js 的规则会带来不必要的 review 噪音和错误建议。
- Risk: 一些贡献者仍可能因为习惯优先引用 `vercel-react-best-practices`；后续仍需要依靠仓库本地规则和 review 意见持续强化新的优先级。
- Date: 2026-03-27
- Scope: frontend styling guidance
- Decision: Updated `docs/skills/tailwind-best-practices-guide.md` and refined `docs/rules/前端开发规范.md` to treat `tailwind-best-practices` as a repo-adapted review reference instead of a directly enforceable rule set.
- Reason: 原始 skill 面向的是 Mastra Playground，假设了不同的组件体系、token 来源，以及比当前仓库更严格的 arbitrary values 与 `className` 覆盖限制；这些前提与本仓库的 Tailwind v4 + shadcn/ui 现状并不一致。
- Risk: 如果读者只看原始 skill 而忽略仓库内的适配说明，评审时仍可能过度套用 Mastra 专属限制；后续前端规范需要继续明确以仓库本地文档为准。
- Date: 2026-03-27
- Scope: frontend standards documentation
- Decision: Updated `docs/rules/前端开发规范.md` to explicitly incorporate the applicable rules from `.agents/skills/react-best-practices/`, including waterfall prevention, bundle constraints, TanStack Query deduplication, React 19 effect/state guidance, and hot-path JavaScript rules.
- Reason: 旧版规范已经覆盖了项目结构和常见前端模式，但还没有把新功能开发和评审中应关注的 React 性能实践明确写成可执行规则。
- Risk: 现有前端代码未必完全满足这套性能导向规范；执行时应优先约束新增或修改代码，避免在非热点路径上机械优化。
- Date: 2026-03-25
- Scope: frontend standards documentation
- Decision: Added `docs/rules/前端开发规范.md` and supporting spec docs based on the current frontend codebase, with a small set of strengthened constraints for future development.
- Reason: 当前前端在路由、请求、表单、样式和生成 client 使用上已经形成了稳定模式，但这些规则此前分散在代码和配置里，没有被显式沉淀成统一规范。
- Risk: 一些已有文件可能暂时还不能完全满足增强后的规则；执行时应以增量方式推进，优先要求新改动对齐规范。
- Date: 2026-03-25
- Scope: frontend CRUD template documentation
- Decision: Added `docs/rules/前端 CRUD 开发模板.md` and supporting spec docs to standardize conventional CRUD page structure, query invalidation, modal forms, and state handling based on existing `items` and `admin/users` patterns.
- Reason: 仓库后续仍会持续增加大量 CRUD 页面，仅靠原则性规范不足以稳定约束布局、交互和数据流；基于现有 `items` 和 `admin/users` 模式沉淀模板更容易直接复用。
- Risk: 这份模板有意偏向标准 CRUD 页面；复杂工作流页面不应被强行套入模板，而应在实际场景下做针对性调整。
