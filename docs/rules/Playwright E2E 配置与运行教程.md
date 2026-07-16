# Playwright E2E 配置与运行教程（本项目）

本教程用于在当前仓库运行浏览器端到端测试（E2E）。项目使用 Playwright `1.61.1`，前端测试配置位于 `frontend/playwright.config.ts`。

## 1. 当前项目的 E2E 运行方式

- Playwright 测试目录：`frontend/tests/`
- 前端地址：`http://localhost:5173`
- 执行测试时，Playwright 会自动运行 `bun run dev` 启动 Vite；本机已有前端服务时会复用它。
- 后端地址默认为 `http://127.0.0.1:8000`，**不会**由 Playwright 自动启动，需单独启动。
- Chromium 项目在每次测试前执行 `frontend/tests/auth.setup.ts`，以根目录 `.env` 的 `FIRST_SUPERUSER` 和 `FIRST_SUPERUSER_PASSWORD` 登录，并保存会话至 `frontend/playwright/.auth/user.json`。

## 2. 前置条件

在开始前，确认已具备：

- Bun（前端依赖和 Playwright 命令）
- uv（后端依赖、Alembic 和 FastAPI 命令）
- PostgreSQL，以及可用的 `createdb`、`dropdb` 命令
- 已安装仓库依赖，并在根目录配置好 `.env`（至少包括数据库连接和初始超级用户变量）

首次安装或 Playwright 报浏览器缺失时，安装 Chromium：

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\frontend
bunx playwright install chromium
```

`--headed` 会打开可见浏览器窗口，应安装完整 Chromium；仅安装 headless shell 不足以运行有界面模式。

## 3. 创建隔离的 E2E 测试数据库

不要对日常开发使用的 `aiadmin` 数据库执行本流程。`backend/tests/conftest.py` 的测试夹具会在结束时删除库存、主数据和用户等测试数据，因此必须使用独立数据库。

以下示例创建名为 `aiadmin_test` 的数据库；如本地 PostgreSQL 用户不是 `postgres`，替换为实际用户名。

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template
createdb -U postgres aiadmin_test

Set-Location backend
$env:POSTGRES_DB = 'aiadmin_test'
uv run alembic upgrade head
uv run python app/initial_data.py
```

`initial_data.py` 会创建 E2E 登录 setup 所需的初始超级用户。根目录 `.env` 中的 `FIRST_SUPERUSER` 与 `FIRST_SUPERUSER_PASSWORD` 必须有效。

> PowerShell 环境变量只对当前终端有效。每个要连接此测试库的后端或测试终端都需要设置 `POSTGRES_DB`。

## 4. 启动后端（终端 A）

在第一个 PowerShell 终端运行：

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\backend
$env:POSTGRES_DB = 'aiadmin_test'
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8000
```

启动后访问 [健康检查](http://127.0.0.1:8000/api/v1/utils/health-check/)，应返回 `true`。

## 5. 运行 E2E（终端 B）

在第二个 PowerShell 终端运行。前端无需提前启动：测试配置会自动启动或复用 `http://localhost:5173` 的 Vite 服务。

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\frontend

# Chromium 无界面运行（默认）
bunx playwright test --project=chromium

# 打开 Chromium，便于观察操作过程
bunx playwright test --project=chromium --headed

# 打开 Playwright UI 调试界面
bunx playwright test --ui
```

也可以使用已定义的脚本：

```powershell
bun run test
bun run test:ui
```

浏览器启动后，可在 `http://127.0.0.1:5173` 确认前端已就绪。

## 6. 运行单个规格文件

新增库存 E2E 后，可按以下方式只运行该文件：

```powershell
Set-Location D:\Workspace\full-stack-fastapi-template\frontend
bunx playwright test tests/inventory.spec.ts --project=chromium --headed
```

当前仓库尚未提供 `frontend/tests/inventory.spec.ts`；该命令用于该文件创建后的定向验证。

## 7. 常见问题排查

### 后端无法连接或接口返回错误

1. 在后端终端确认 `POSTGRES_DB` 为测试数据库名。
2. 重新执行 `uv run alembic upgrade head`。
3. 重新执行 `uv run python app/initial_data.py`，确保测试登录使用的超级用户存在。
4. 访问健康检查地址，确认后端在 `127.0.0.1:8000` 运行。

### `Executable doesn't exist` 或找不到浏览器

在 `frontend` 目录重新运行：

```powershell
bunx playwright install chromium
```

### 登录 setup 失败或找不到环境变量

`frontend/tests/config.ts` 从仓库根目录 `.env` 读取 `FIRST_SUPERUSER` 和 `FIRST_SUPERUSER_PASSWORD`。确认这两个变量已设置，并确认已在测试数据库执行过 `initial_data.py`。

### 前端端口被占用

默认情况下，`playwright.config.ts` 会复用已有的 `5173` 服务。若该服务不是当前工作区启动的 Vite，停止占用进程后重新运行测试，或先手动在当前工作区执行 `bun run dev`。

## 8. 清理测试数据库

不再需要测试数据时，停止后端后执行：

```powershell
dropdb -U postgres aiadmin_test
```

## 9. 与 Codex 交互式浏览器的区别

以上 Playwright E2E 不依赖 Codex 的交互式浏览器连接：只要本机安装 Chromium、后端可用，即可运行。

Codex 驱动的可视化点击、截图和页面检查则需要在 Codex 中附加或启用浏览器会话。此前本地前后端虽可正常返回 `200`，但 Codex 浏览器运行时没有可用浏览器，因而无法进行该类交互验证；这不是仓库内 Playwright 配置能够单独解决的问题。
