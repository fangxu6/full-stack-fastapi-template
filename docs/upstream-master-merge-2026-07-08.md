# 2026-07-08 upstream master 合并说明

## 背景

本仓库在 `2026-07-08` 将官方仓库 `https://github.com/fastapi/full-stack-fastapi-template` 的 `master` 合并到本地 `master`。

- 本地合并提交：`cd0eeaf Merge branch 'master' of https://github.com/fastapi/full-stack-fastapi-template`
- 本地合并前基线：`26ffe37 chore(task): archive 06-30-refresh-codebase-specs`
- upstream 合入目标：`4cd0d9e Update release notes`
- 合并范围：`36 files changed, 785 insertions(+), 2004 deletions(-)`

## 主要更新

### 依赖与运行时

- 新增 `.python-version`，upstream 侧开始显式声明 Python 版本。
- `backend/pyproject.toml`、`uv.lock` 更新，包含 FastAPI、Sentry、emails、测试与静态检查相关依赖升级。
- `frontend/package.json`、`bun.lock` 更新，包含 React、TanStack Router / Query、Radix UI、Playwright、Vite、Biome、Zod 等前端依赖升级。
- `frontend/Dockerfile.playwright` 同步 Playwright 镜像版本。

### 后端与生成客户端

- `backend/Dockerfile` 改为 FastAPI entrypoint 相关更新。
- `backend/app/core/config.py`、`backend/app/core/security.py`、`backend/app/utils.py` 同步 upstream 的配置、安全与工具函数调整。
- `frontend/src/client/schemas.gen.ts`、`frontend/src/client/types.gen.ts` 重新生成，匹配合并后的 OpenAPI 类型。

### CI 与自动化

- `.github/workflows/*` 多个 workflow 同步更新，包括测试、Playwright、pre-commit、deploy、smokeshow、latest-changes、zizmor 和 issue-manager。
- `.github/dependabot.yml` 调整 Dependabot 计划。
- `.pre-commit-config.yaml` 与顶层 `pyproject.toml` 同步 upstream 的工具配置更新。

### AI / Skill 支持

- 新增 `.agents/skills/fastapi`、`.agents/skills/sqlmodel`。
- 新增 `.agents/skills/library-skills/`。
- 同步新增 `.claude/skills/fastapi`、`.claude/skills/sqlmodel` 与 `.claude/skills/library-skills/`。

这些文件来自 upstream 的 library-skills 支持，用于把 FastAPI / SQLModel 相关开发指导暴露给支持 skills 的 AI 工具。

## 远端新增文件重点说明

本次从官方 upstream 新增 9 个文件。它们不是业务代码文件，主要分为 Python 版本声明和 AI skill 管理两类。

| 新增文件 | 作用 | 对本地仓库的影响 |
| --- | --- | --- |
| `.python-version` | 声明项目 Python 版本为 `3.14` | 本地 `uv`、`pyenv` 或 IDE 可能优先按该文件选择 Python 3.14；如果机器没有对应解释器，需要先安装或调整本地 Python 管理配置 |
| `.agents/skills/fastapi` | 指向 FastAPI 包内置 agent skill 的链接/指针 | 让支持 `.agents/skills` 的 agent 在依赖安装后能读取 FastAPI 开发指导；目标依赖 `.venv/lib/python3.14/site-packages/fastapi/...` |
| `.agents/skills/sqlmodel` | 指向 SQLModel 包内置 agent skill 的链接/指针 | 让支持 `.agents/skills` 的 agent 在依赖安装后能读取 SQLModel 开发指导；目标依赖 `.venv/lib/python3.14/site-packages/sqlmodel/...` |
| `.agents/skills/library-skills/.library-skills.json` | 标记该目录由 `library-skills` 管理，当前工具 skill 版本为 `0.0.19` | 后续应优先通过 `uvx library-skills` / `npx library-skills` 检查和修复，不建议手工改这些托管链接 |
| `.agents/skills/library-skills/SKILL.md` | 说明如何发现、安装、刷新、修复包内置 skills | 给通用 agent / Codex 类工具提供操作说明，例如 `uvx library-skills list --json`、`uvx library-skills --check`、`uvx library-skills --yes` |
| `.claude/skills/fastapi` | Claude Code 侧的 FastAPI skill 链接/指针 | 与 `.agents/skills/fastapi` 作用相同，但面向读取 `.claude/skills` 的工具 |
| `.claude/skills/sqlmodel` | Claude Code 侧的 SQLModel skill 链接/指针 | 与 `.agents/skills/sqlmodel` 作用相同，但面向读取 `.claude/skills` 的工具 |
| `.claude/skills/library-skills/.library-skills.json` | Claude Code 侧的 `library-skills` 管理标记 | 表示 `.claude/skills/library-skills` 同样是工具托管内容 |
| `.claude/skills/library-skills/SKILL.md` | Claude Code 侧的 Library Skills 操作说明 | 与 `.agents` 下的 `SKILL.md` 内容一致，用于 Claude Code 读取项目内 skill 管理流程 |

### 新增文件的使用注意

- `.agents/skills/fastapi`、`.agents/skills/sqlmodel`、`.claude/skills/fastapi`、`.claude/skills/sqlmodel` 是指向 `.venv/lib/python3.14/site-packages/...` 的 managed skill 链接/指针。它们依赖本地依赖安装结果；如果 `.venv` 被删除、Python 版本路径改变或依赖尚未安装，这些 skill 可能暂时不可用。
- `library-skills` 文档明确建议：依赖安装后运行 `uvx library-skills` 或 `npx library-skills` 来发现和安装包内置 skills；运行 `uvx library-skills --check` 检查托管链接；运行 `uvx library-skills --yes` 非交互修复 stale / orphaned managed symlinks。
- 这些新增文件会影响 AI 工具的上下文加载方式，但不会直接改变 FastAPI 后端、React 前端或数据库运行逻辑。
- 如果本地不希望 Claude Code 读取 `.claude/skills`，需要另行决定是否保留这些 upstream 新增文件；本次合并按 upstream 保留。

### 文档

- `README.md` 同步 upstream 的展示文案调整。
- `release-notes.md` 同步 upstream 最新 release note，包含 upstream 近期功能、重构、依赖升级、文档和内部维护记录。

## 冲突处理记录

本次合并出现 5 处冲突，均已解决：

| 文件 | 处理方式 | 原因 |
| --- | --- | --- |
| `backend/app/api/deps.py` | 保留本地 `dependencies` re-export 结构 | 本地已经将 API 依赖拆到 `backend/app/api/dependencies/`，旧的单文件实现不应回退 |
| `backend/app/models.py` | 保留本地删除结果 | 本地已经拆分为 `backend/app/models/` 和 `backend/app/schemas/`，upstream 的旧单文件 `models.py` 不再适合当前结构 |
| `frontend/src/routes/_layout.tsx` | 保留本地 `AppLayout` + `requireLogin` 路由结构 | 本地已经抽出应用布局和路由 guard，upstream 内联布局会倒退当前分层 |
| `frontend/src/routes/signup.tsx` | 保留本地 `SignUpPage` 分层 | 本地已经将注册页实现移动到 `platform/auth/pages/SignUpPage.tsx` |
| `frontend/package.json` | 采用 upstream 版本 | 该冲突主要是依赖版本差异，upstream 版本代表本次合并目标的最新依赖集合 |

## 验证结果

已完成：

- `git diff --check` 通过。
- `git diff --cached --check` 通过。
- 冲突标记扫描通过，没有残留 `<<<<<<<`、`=======`、`>>>>>>>`。
- 合并过程已结束，`MERGE_HEAD` 不存在。

未完成：

- `uv run pytest backend/tests -q` 未能进入测试用例执行阶段。
- 失败原因是当前本地环境缺少必需配置项：`PROJECT_NAME`、`POSTGRES_SERVER`、`POSTGRES_USER`、`FIRST_SUPERUSER`、`FIRST_SUPERUSER_PASSWORD`。
- 该失败属于测试环境配置缺失，不是已知的代码冲突残留。

## 工作区注意事项

合并前的本地未提交内容已通过临时 stash 保护，并在合并提交后恢复。它们没有被纳入 `cd0eeaf`：

- `docs/README.md`
- `.trellis-other/`
- `.trellis/tasks/07-08-trellis-helper-script-parity/`
- `.trellis/tasks/07-08-trellis-workflow-parity/`
- `docs/rules/AI编码工作流.md`

## 后续建议

1. 补齐本地测试环境变量后重新运行 `uv run pytest backend/tests -q`。
2. 如需前端验证，运行 `bun install` 后再执行前端 lint / test / build。
3. 后续如果继续同步 upstream，优先关注模型拆分、路由分层、AI skills 文件和依赖锁文件的冲突。
