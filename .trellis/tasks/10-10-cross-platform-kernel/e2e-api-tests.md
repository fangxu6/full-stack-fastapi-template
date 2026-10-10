# e2e-api-tests.md — 内核落地侧执行条件

**本文件不重复定义用例。** 用例定义在父任务 [e2e-api-tests.md](../10-10-react-native-app/e2e-api-tests.md)，本任务负责执行其中的 **E2E-009、E2E-010**。

## 为什么不在本文件重复

父任务是跨层集成任务，持有权威的跨层 E2E 计划。若在两个文件各写一份，会出现两处真相源——正是本方案（D5）要消除的失败模式。因此本文件只补充**执行归属与判据**。

## 本任务执行的用例

| ID | 在本任务中的含义 |
| --- | --- |
| E2E-009 | **契约生成一致性**：`bash ./scripts/generate-client.sh` 成功后 `git diff --exit-code` 为空 |
| E2E-010 | **Web 侧回归**：`bun run build` / `bun run lint` / `check-thin-routes` / `run_quality_hooks.py --json` 全部通过 |

## 本任务不执行的用例

E2E-001 ~ E2E-008 需要运行后端并由 App 消费，属 `10-10-mobile-app-slice`。本任务**不新增或修改任何后端接口**（Out of Scope），因此无需在此阶段起后端。

## Execution

```bash
# 契约生成链路（E2E-009）
bash ./scripts/generate-client.sh && git diff --exit-code

# Web 回归（E2E-010）
bun run build
bun run lint
python hooks/run_quality_hooks.py --json

# 门禁
bun test scripts/check-cross-platform-boundaries.test.ts
bun test scripts/check-thin-routes.test.ts

# 空白/行尾检查
git diff --check
```

## 关键判据

- **E2E-009 的 `git diff` 必须为空。** 任何 diff 都说明生成链路未完整迁移（旧路径残留或未跟踪产物），必须修复后才能进入 `10-10-mobile-app-slice`。
- **E2E-010 的 4 条命令必须全绿。** 这是父任务 **AC6** 的直接证据，也是本任务「Web 行为不变」承诺的唯一客观验证手段。
- 额外人工判据：`git diff --stat` 中**不得出现任何 `frontend/src/**` 消费者文件**——这是「38 个消费者零改动」的证据。

## 与父任务 AC5 的关系

本任务交付共享层并保证 Web 行为不变，但 AC5 还要求 `mobile` 真实引用共享层——那在子任务 2 完成后由父任务集成复核。本任务**不单独验收 AC5**。

## 环境说明

本任务不需要后端运行，因此不存在「隔离环境」要求。但 `bun run build` / `bun run lint` 需要完整的 workspace 依赖，故执行前须先 `bun install`。
