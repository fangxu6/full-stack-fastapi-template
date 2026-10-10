# e2e-api-tests.md — App 侧执行条件

**本文件不重复定义用例。** 用例定义在父任务 [e2e-api-tests.md](../10-10-react-native-app/e2e-api-tests.md)，本任务负责执行其中的 **E2E-001 ~ E2E-008**。

## 为什么不在本文件重复

父任务是跨层集成任务，持有权威的跨层 E2E 计划。若在两个文件各写一份，会出现两处真相源——正是本方案（D5）要消除的失败模式。因此本文件只补充**执行归属与 App 侧前置条件**。

## 本任务执行的用例

| ID | 在本任务中的额外含义 |
| --- | --- |
| E2E-001 | 确认隔离后端可达，且 Android 真机能访问到同一地址（注意真机不能用 `localhost`，须用局域网 IP） |
| E2E-002 | App 登录页真实调用；断言 token 写入 `expo-secure-store`（不是 `localStorage`） |
| E2E-003 | 首页入口过滤的依据；断言 `hasPermission()` 结果与后端返回一致 |
| E2E-004 | **扫码主链路**：扫到的单据号作为 `document_number` 查询参数 |
| E2E-005 | 单据明细页 |
| E2E-006 | 库存余额页 |
| E2E-007 | **AC4 核心**：只有 `inventory.documents.read` 的用户，余额入口不显示；直接访问余额页后端返回 `403` |
| E2E-008 | 无 `inventory.documents.read` 的用户，单据入口不显示；直接访问返回 `403` |

## App 侧前置条件（父任务用例之外的部分）

1. **后端地址**：Android 真机无法解析 `localhost`。必须把 `baseUrl` 指向本机局域网 IP（例如 `http://192.168.x.x:8000`），并确认后端监听 `0.0.0.0` 或该网卡地址。
2. **隔离环境**：使用任务独立的隔离数据库；**不得写入开发库**。若本机无可用隔离环境，只有在实际尝试之后才可记录具体阻塞项。
3. **两个权限组合的用户**（E2E-007 / E2E-008 必需）：
   - 用户 A：`inventory.documents.read` + `inventory.balances.read`
   - 用户 B：**只有** `inventory.documents.read`（用于验证余额入口隐藏 + 403）
   - 用户 C：无 `inventory.documents.read`（用于验证单据入口隐藏 + 403）
4. **扫码数据**：隔离库中需存在一条 `document_number` 已知的单据。若隔离库为空，经后端**既有**接口写入测试单据。
5. **真机要求**：`expo-camera` 在模拟器中不可用，扫码用例（E2E-004 的扫码分支）**必须在 Android 真机 + Expo Go 上执行**。
6. **未命中分支**：额外用一个不存在的单据号（如 `ZZZ-NOT-EXIST`）验证「未命中提示」。后端对此返回 `200` + 空列表，App 必须显式提示，不得静默失败。

## Execution

```bash
# 1. 起隔离后端并确认健康
curl -s http://127.0.0.1:8000/api/v1/utils/health-check/

# 2. 起 App（真机扫码）
bun run --filter mobile start

# 3. 用真机 Expo Go 扫码打开，按上表逐条执行
```

- 把命令输出、真机截图或结论记入本任务 `implement.md` 的 Validation Notes。
- 环境不可用时记录**具体阻塞项**，不得把环境失败记为通过。

## 与父任务 AC5 的关系

本任务不单独验收 AC5（它属于父任务的集成复核）。但本任务**必须**让 `mobile/` 真实 import `@repo/domain` 与 `@repo/tokens`（而非只声明依赖），否则父任务 AC5 无法成立。
