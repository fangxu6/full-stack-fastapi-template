# Implementation Spec

## Goal Summary
- 在后端增加一个受保护的 rules 文档只读能力，并通过 OpenAPI 暴露给前端。
- 在前端受保护布局中增加 `/rules` 页面，展示规则列表与单篇原文。
- 采用最小闭环实现，后续可复用同类模式扩展到 `docs/specs/**` 或其他文档目录。

## File Changes
- `backend/app/schemas/docs.py`
- `backend/app/services/docs.py`
- `backend/app/services/__init__.py`
- `backend/app/api/routes/docs.py`
- `backend/app/api/main.py`
- `backend/tests/api/routes/test_docs.py`
- `frontend/src/routes/_layout/rules.tsx`
- `frontend/src/components/Sidebar/AppSidebar.tsx`
- `docs/decisions/AI_CHANGELOG.md`
- `docs/specs/rules-viewer-mvp/*`
- generated:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`

## Data Changes
- 无数据库变更。
- 无 migration。
- 新增只读文档元数据与内容响应 schema。

## Core Flow (Pseudo)
1. 后端扫描仓库根目录 `docs/rules/*.md`，构建白名单索引。
2. 白名单索引只接受普通 `.md` 文件，拒绝 symlink，并确认真实路径仍位于白名单目录内。
3. 列表接口返回规则摘要数组。
4. 详情接口按 slug 命中白名单后读取文件内容。
5. 前端 `/rules` 页面先请求列表。
6. 若 search 中无 slug，则默认展示首篇；若有 slug，则请求对应详情。
7. 页面展示加载态、空态、错误态与正文。

## Validation & Errors
- 仅允许白名单命中的 slug；未命中返回 `404 Rule document not found`。
- 若白名单目录不存在，列表返回空数组。
- symlinked `.md` 文件不能进入白名单，也不能被详情接口读取。
- 详情读取到目录外文件时返回 `404`，不暴露底层路径信息。
- 前端如果详情请求失败，应保持页面稳定并给出错误反馈。

## Execution Plan
- Step 1: 新增 backend docs schema、service、route 与 API tests。
- Step 2: 重新生成 OpenAPI client。
- Step 3: 新增前端 `/rules` 页面与侧边栏入口。
- Step 4: 运行 targeted tests、lint、build，并更新决策记录。

## Rollback
- 移除 `docs` API route 与前端 `/rules` 页面、侧边栏入口即可回滚。
- 因为不涉及数据库和持久化，回滚风险主要在前端导航和 OpenAPI client 变更。
