# implement.md — 父任务：跨端方案集成落地

本任务是**集成型父任务**（D8），不直接实现代码。它持有完整需求集、任务地图、跨子任务验收项（AC5）与最终集成复核。

## 任务地图

| 任务 | 类型 | 覆盖 AC | 前置 |
|---|---|---|---|
| `10-10-cross-platform-kernel` | 子任务（实施） | AC1、AC6、AC7、AC8 | 无 |
| `10-10-mobile-app-slice` | 子任务（实施） | AC2、AC3、AC4、AC9 | **子任务 1 完成** |
| `10-10-react-native-app`（本任务） | 父任务（集成） | **AC5** | 两个子任务完成 |

依赖关系写在子任务自身的产物里，不靠树位置暗示。

## 执行顺序

1. **子任务 1** 完成并通过出口条件（Web 全绿、生成链路 `git diff` 为空）。
2. **子任务 2** 开始（依赖子任务 1 产出的 `packages/contract` 与 `packages/domain`）。
3. **父任务** 集成复核，验收 AC5。

子任务 1 未完成时，子任务 2 不得启动——它需要的 `@repo/contract` / `@repo/domain` 尚不存在。

## 父任务验收：AC5

> AC5：共享层被两端真实引用（不是"建了目录没人用"），且 Web 侧引用共享层后行为不变。

这一条**无法在任一子任务内单独验证**，因为它要求两端同时存在。集成复核的具体检查项：

- [ ] `frontend` 真实 import `@repo/domain` / `@repo/tokens`——不是只有再导出文件存在，而是 `frontend/src/**` 中有实际消费点
- [ ] `mobile` 真实 import `@repo/domain` / `@repo/tokens`
- [ ] Web 侧行为不变：`e2e-api-tests.md` 的 E2E-009（契约生成一致）+ E2E-010（Web 构建与校验）
- [ ] 门禁规则 4 通过：`/api/v1/` 字符串字面量只出现在 `packages/domain` 与 `packages/contract`
- [ ] `frontend` 与 `mobile` 无任何互相引用
- [ ] 上端矩阵中 `inventory` 条目为 `["web","app"]`，且 `app_scope` 与实际实现的页面一致

**注意"再导出不算引用"**：子任务 1 在 `frontend/src/client/index.ts`、`frontend/src/shared/permissions/index.ts`、`frontend/src/app/permissions.ts` 留了再导出 shim。这些 shim 证明**依赖方向已迁移**，但 AC5 要求的是**真实消费**。因此复核时必须确认：Web 侧至少有一个业务文件通过 `@repo/domain` 的 API 工作（例如 `features/inventory` 改用了 `@repo/domain` 的查询函数），而不只是路径间接。

## 最终集成验证命令

```bash
bun install
bun run build
bun run lint
python hooks/run_quality_hooks.py --json
bun test scripts/check-cross-platform-boundaries.test.ts
bun test scripts/check-thin-routes.test.ts
bash ./scripts/generate-client.sh && git diff --exit-code
```

最后一条是关键门禁：重新生成客户端后 `git diff` 必须为空，证明生成链路已完整迁移到 `packages/contract`，没有残留的旧路径。

## Review Gate

集成复核通过后才可 `task.py finish`。任一子任务未达出口条件时，父任务不得归档。

## Rollback Points

| 情形 | 回滚方式 |
|---|---|
| 子任务 1 未完成 | 父任务保持 planning；Web 不受影响（迁移全程有再导出 shim 兜底） |
| 子任务 1 完成、子任务 2 失败 | 子任务 1 独立成立（Web 仍绿、共享层已落地）；父任务不归档，AC5 保持未满足 |
| 集成复核发现 Web 回归 | 回退子任务 1 的再导出改动（恢复原文件）；`packages/*` 可保留待重试 |

## 明确不做

- 不新增或修改后端接口与字段（Out of Scope）
- 不做应用商店上架、签名证书、CI/CD 发布流水线
- 不做 Web 功能的全量移动端对等迁移
- 不做 iOS 构建与验证（D4）

## 关联产物

- 需求与决策：[prd.md](prd.md)（D1–D8）
- 技术设计：[design.md](design.md)
- 跨层 E2E：[e2e-api-tests.md](e2e-api-tests.md)
- 外部系统参考：[research-zqsystem-cross-platform.md](research-zqsystem-cross-platform.md)
