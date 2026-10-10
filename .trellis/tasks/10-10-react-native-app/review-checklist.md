# review-checklist.md — 规划审核清单

> 用途：改日审核这份跨端规划时逐条勾选。本文件**只用于审核**，不是实施计划（实施看 `implement.md`）。
>
> 审核对象：本目录 `prd.md`（D1–D8）、`design.md`、`implement.md`、`e2e-api-tests.md`，以及两个子任务 `10-10-cross-platform-kernel` / `10-10-mobile-app-slice`。
>
> 审核通过后：`python ./.trellis/scripts/task.py start 10-10-cross-platform-kernel`

---

## 0. 先读这一节：本机 shell 输出不可信

**在核验任何数字之前必须知道这件事**，否则你会得到假结论。

本机（Windows/MSYS bash）每条 bash 命令都经过 `/d/scoop/shims/rtk` 包装器，它会改写 stdout：剥离公共路径前缀、把文件列表折叠成 `dir/ (N files)` 摘要、**有时整段丢弃**。

本轮审核中它确实骗过我一次：`git grep -l '@/client/'` 返回 **0**，但深路径 import 实际存在。加上转义 `git grep -n '@\/client\/'` 才拿到正确的 2 个文件。

**可靠做法（任选其一）**：

```bash
# 1) 重定向到文件再读
command > /tmp/out.txt 2>&1; cat /tmp/out.txt

# 2) 用转义的正则形式（对 git grep 有效）
git grep -n '@\/client\/'

# 3) 直接用 pi 的原生工具 ffgrep / anchor_grep / read（最可靠）
```

**判定规则**：任何"0 结果"或"文件列表被折叠"的输出，都**不得**直接当作事实。用上面任一种方式复核后再下结论。

---

## 1. 关键事实核验（可复现）

逐条运行，把实测值填进"实测"列。**若与"本文档声称"不符，本规划需要修订。**

| # | 声称 | 复现命令 | 本文档声称 | 实测 | ✓ |
|---|---|---|---|---|---|
| F1 | `@/client` 消费者数 | `git grep -l '"@/client"' -- 'frontend/src/**' \| wc -l` | **38** | | ☐ |
| F2 | 其中额外用深路径的文件数 | `git grep -n '@\/client\/' \| grep -v '\.trellis/'` | **2**（`inventory/api.ts:10`、`excel.ts:2`） | | ☐ |
| F3 | 生成物文件数 / 行数 | `git ls-files 'frontend/src/client/**' \| wc -l` / `... \| xargs wc -l \| tail -1` | **10 文件 / 5706 行** | | ☐ |
| F4 | 提及 `src/client` 的规格+钩子+脚本文件数 | `git grep -l 'src/client' -- '.trellis/spec/**' 'hooks/**' 'scripts/**' 'frontend/biome.json' \| wc -l` | **19** = 15 规格 + 2 钩子 + 1 脚本 + biome | | ☐ |
| F5 | 规格文件细分 | 同上，按目录分类 | backend **6** / frontend **6** / guides **2** / `spec/index.md` **1** | | ☐ |
| F6 | `generate-client.sh` 引用 frontend 路径的行 | `cat -n scripts/generate-client.sh` | 第 **7、9、10、11、12** 行（共 5 行） | | ☐ |
| F7 | `normalize-...mjs` 是否需要改逻辑 | `sed -n '1,25p' scripts/normalize-generated-client-whitespace.mjs` | **否**，它接受 `directory` 参数；只改调用点 | | ☐ |
| F8 | 钩子允许列表位置 | `sed -n '14,20p' hooks/quality_hooks/frontend.py` | `GENERATED_ARTIFACT_PATHS` 含 `"frontend/src/client"`（第 **17** 行） | | ☐ |
| F9 | 钩子测试夹具位置 | `sed -n '48,54p' hooks/tests/test_quality_hooks.py` | `frontend/src/client/types.gen.ts`（第 **51** 行） | | ☐ |
| F10 | 当前 workspace 成员 | `node -e "console.log(require('./package.json').workspaces)"` | `['frontend']`（无共享包层） | | ☐ |
| F11 | 后端有无条码字段 | `git grep -ni 'barcode\|scan_code' -- 'backend/app/**'` | **无匹配**（D7 的前提） | | ☐ |
| F12 | balances 是否支持 `item_code` | `git grep -n 'item_code' -- 'backend/app/modules/inventory/router.py'` | **不支持**（D7 规避的原因） | | ☐ |
| F13 | 两个权限码是否不同 | `git grep -n 'inventory.documents.read\|inventory.balances.read' -- 'backend/app/modules/inventory/router.py'` | **不同**（AC4 的验证基础） | | ☐ |
| F14 | 本机无 Android/iOS 工具链 | `which adb gradle xcodebuild; echo $ANDROID_HOME` | 全部缺失（D3 的前提） | | ☐ |

---

## 2. 决策审核（D1–D8）

每条给出「不同意时的代价」，供你判断是否值得改。

| 决策 | 内容 | 不同意时的代价 | ✓ |
|---|---|---|---|
| **D1** | 共享领域内核 + 各端独立 UI | 换 B（react-native-web 单代码库）需**重写现有 Web UI**并牺牲 antd 后台表格（本仓库有 578 行 inventory 页面）；换 C（仅共享类型）等于 zqsystem 现状 | ☐ |
| **D2** | `packages/{contract,domain,tokens}` + `mobile/` | 换单包 → 边界只能靠目录约定，无法用工具禁止 domain 依赖 antd；换 TS path alias → `mobile`/`frontend` 互相耦合 | ☐ |
| **D3** | Expo（Expo Go 起步） | 换 bare RN CLI → **必须先装 Android Studio + SDK** 才能跑第一行代码 | ☐ |
| **D4** | 只做 Android | 换 A/B → 需 Apple 账号（$99/年）+ EAS iOS 签名，且本机无法本地调试 iOS | ☐ |
| **D5** | 强制内核共享 + 显式上端矩阵，不强制 UI 对等 | 换 B（UI 对等）→ 强制产出无价值的移动端后台页面（inventory 217~578 行 + antd 表格 + excel 导入导出） | ☐ |
| **D6** | 首批 = 登录 + 只读 + 扫码 | 换 C（含离线）→ 需设计离线数据模型 + 同步/冲突策略，且后端无离线接口 | ☐ |
| **D7** | 扫码目标 = `document_number` | 换 B（扫品名）→ balances 不支持 `item_code`，扫货号无效；换 C（结构化二维码）→ 需先约定码格式且 ledger 需 5 段复合键 | ☐ |
| **D8** | 父任务 + 2 子任务 | 换 A（单任务）→ 一条超长变更历史，P1 失败时 App 工作已被牵连 | ☐ |

---

## 3. 需要你明确表态的 3 个高风险设计决定

这 3 处是**判断题**，不是事实题。我给出了理由，但只有你能确认取舍是否可接受。

### 3.1 生成物用「再导出 shim」而非改 38 个消费者

`design.md` §4.1。`frontend/src/client/` 保留 3 个单行文件（`index.ts` + `core/request.ts` + `core/ApiRequestOptions.ts`），全部再导出 `@repo/contract`。

- **收益**：38 个消费者**一行不改**，AC6 风险最小。
- **代价**：`frontend/src/client/` 这个目录名从此名不副实（里面不再是生成物）。
- ☐ 认可　☐ 改为改写 38 个 import（更干净但风险大）

### 3.2 权限真相源搬迁后保留 Web 侧再导出

`design.md` §5.4。`shared/permissions/index.ts` 与 `app/permissions.ts` 变成再导出，真相源移到 `packages/domain`。

- **关键**：`.trellis/spec/frontend/route-permission-navigation-contract.md` 现在明文写着权限真相源 "remain in `shared/permissions/*`"。**该 spec 必须改措辞**，否则 spec 与代码矛盾。
- ☐ 认可（并接受该 spec 是强制更新项）　☐ 改为不搬迁权限（共享层少一块，AC5 变弱）

### 3.3 15 个规格文件中，C 类「不改」

`10-10-cross-platform-kernel/implement.md` 的同步清单把 `frontend/biome.json:10`、`hooks/quality_hooks/frontend.py:17`、`hooks/tests/test_quality_hooks.py:51` 列为**不改**，理由是 shim 让 `frontend/src/client/**` 路径仍然存在。

- **风险**：如果实施时 shim 策略调整（例如改成 3.1 的"改写 38 个 import"），这 3 处**必须**跟着改。
- ☐ 认可　☐ 改为一并更新（更保守）

---

## 4. 本规划中我自查纠正的错误（供你核对我的可信度）

这些是我在规划过程中发现并已修正的错误。**列出它们是让你知道哪些地方曾经错过，从而重点复核。**

| # | 我曾说 | 实际 | 在哪修正 |
|---|---|---|---|
| 1 | 相机/扫码/安全存储需 development build | **都在 Expo Go 中**；只有远程推送需要 | `prd.md` D3 + 「Expo Go 能力边界」表 |
| 2 | 迁移爆炸半径 = 38 个文件 | **38 消费者 + 15 规格 + 2 钩子 + 1 脚本 + biome** | `design.md` §4.1 表 |
| 3 | 只需 1 个再导出 shim | 需 **3 个**（2 个文件额外用深路径） | `design.md` §4.1 |
| 4 | 38 = 36 走 index + 2 走深路径 | **全部 38 走 index，其中 2 个额外走深路径** | `design.md` §4.1 + 子任务 1 `prd.md` |
| 5 | 规格文件「约 16 个」，含 `spec/log.md` | **15 个**，`spec/log.md` **不含** `src/client` | `design.md` §4.1 表 |
| 6 | 生成脚本「2 处」；`biome ci --no-errors-on-error` | **1 个脚本的 5 行**；参数是 `--no-errors-on-unmatched` | `design.md` §4.1 |

**其中 #4 与 #5 是由第 0 节的 rtk 假输出引发的**——这也是为什么第 0 节必须放在最前面。

---

## 5. 范围承诺审核（改起来最贵）

这两条是**范围**承诺，不是技术选型。技术可以迭代，范围承诺一旦接受就会影响很久。

- ☐ **D4 放弃 iOS 用户**：本迭代不配置任何 iOS 构建/签名/验证。`mobile/` 代码保持 iOS 兼容，但**无验收价值**。
- ☐ **D5 接受「某些功能永远不上 App」**：inventory 的部分页面、scheduler、iam 治理页、docs 等明确 `Web only`。上端矩阵会把这些固化下来。

---

## 6. 子任务拆分与依赖审核

| 检查项 | ✓ |
|---|---|
| 子任务 1（`cross-platform-kernel`）先做，且**不依赖**子任务 2 | ☐ |
| 子任务 2（`mobile-app-slice`）**依赖**子任务 1，且该依赖写在子任务 2 的 `prd.md`/`implement.md` 里（不靠树位置暗示） | ☐ |
| **AC5 留在父任务**（"共享层被两端真实引用"无法在任一子任务内验证） | ☐ |
| 父任务 `implement.md` 明确了「再导出不算引用」这一判据 | ☐ |
| 每个子任务的 `implement.jsonl` / `check.jsonl` 已 curate 且 `task.py validate` 通过 | ☐ |

依赖关系（写死在产物里）：

```
10-10-cross-platform-kernel  ──→  10-10-mobile-app-slice
        (AC1/AC6/AC7/AC8)                  (AC2/AC3/AC4/AC9)
                    ↘                ↙
              10-10-react-native-app (AC5，集成复核)
```

---

## 7. 实施前置条件（环境缺口）

审核通过 ≠ 可以立刻开工。以下缺口会在实施时立刻撞上：

| # | 缺口 | 影响 | 何时需要 | ✓ |
|---|---|---|---|---|
| P1 | 本机**无 Android SDK / adb / gradle / Android Studio** | 子任务 2 的 Expo Go 路径**不需要**它；但一旦需要 development build 或 `expo prebuild` 就必须装 | 子任务 2 步骤 1 起（若只走 Expo Go 则不需） | ☐ |
| P2 | 需一台 **Android 真机 + Expo Go**，且与开发机同局域网 | AC9（扫码）**必须真机**，模拟器不支持 `expo-camera` | 子任务 2 步骤 7 | ☐ |
| P3 | 需**隔离数据库** + 两个不同权限组合的用户 | AC4 的 403 验证必需 | 子任务 2 的 E2E-001~008 | ☐ |
| P4 | 后端需监听局域网地址（真机不能用 `localhost`） | 子任务 2 的 `baseUrl` | 子任务 2 步骤 2 | ☐ |
| P5 | 无 iOS 工具链（Windows） | 不影响本迭代（D4），但未来补 iOS 需 Mac 或 EAS | 未来 | ☐ |

---

## 8. 审核结论

- ☐ **通过**：`python ./.trellis/scripts/task.py start 10-10-cross-platform-kernel`
- ☐ **有条件通过**：需修改以下条目（列出 D/AC/文件与行）：

  ```
  （待填）
  ```

- ☐ **需重做规划**：原因

  ```
  （待填）
  ```

审核人：　　　　　　　日期：

---

## 附：本规划明确不做的事（防止审核时误期待）

- 不新增或修改任何后端接口与字段（Out of Scope；D7 的选型正是为了守住这条）
- 不做应用商店上架、签名证书、CI/CD 发布流水线
- 不做 Web 功能的全量移动端对等迁移
- 不做 iOS 构建与验证（D4）
- **本次提交不含任何产品代码**——只有规划产物
