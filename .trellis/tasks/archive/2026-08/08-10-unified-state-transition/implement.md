# 统一状态迁移执行计划

## 实施顺序

1. 重读 `docs/state-machine-unified-transition-design.md`、当前模型和生命周期实现，保留已有正确的方案说明，删除“尚未创建 Trellis 任务”等已过期描述。
2. 在方案文档增加“枚举、状态与矩阵”的判别规则，声明它是四类既有工作流矩阵的唯一规范来源，并记录不建设全局运行时的边界。
3. 使用统一标题与六个固定列，回填七张矩阵：scheduler run；库存纠错 request、work item、attempt；Email Outbox；日报 report、delivery。每行标明代码锚点、前置条件、副作用和幂等/并发含义；对调用方约束与函数内校验不一致之处如实标注，不修复运行时代码。
4. 新建 `state-transition-guidelines.md`，按照 code-spec 七段结构写入触发条件、命名、矩阵列、领域所有权、事务和测试规则，以及全局运行时/注册中心禁令。
5. 将新规则加入 `.trellis/spec/backend/index.md`，并在 `database-guidelines.md` 和 `directory-structure.md` 添加最小交叉引用；保持已有数据库枚举和模块边界规则为唯一详细来源。
6. 更新 `docs/README.md`，使统一方案文档可发现；执行 `spec_wiki.py index` 刷新全局 `.trellis/spec/index.md` 的受管文件清单，并用 `spec_wiki.py log` 追加本次规范变更记录。
7. 不修改 `async-task-guidelines.md`、归档 Trellis 任务、ADR、应用代码、schema、迁移或前端。完成后进行链接、结构和 diff 范围检查。

## 验证

```bash
python3 ./.trellis/scripts/task.py validate .trellis/tasks/08-10-unified-state-transition
python3 ./.trellis/scripts/spec_wiki.py index --check
python3 ./.trellis/scripts/spec_wiki.py lint
git diff --check
rg -n "状态迁移矩阵|State Transition Matrix|ALL_TRANSITIONS|state-transition-guidelines" docs .trellis/spec
git diff --name-only
```

人工检查项：

- 统一方案文档恰有七张回填矩阵，标题和六列都符合命名规范。
- 每张多对象/租约矩阵都明确事务、前置条件、副作用与幂等/并发，而不是只罗列状态名。
- 新规则明确普通分类 enum 不需要矩阵，且不把矩阵说成数据库表或通用运行时。
- 所有本地 Markdown 链接有效，全局 spec 文件清单和日志已更新。
- 变更文件只属于 `docs/**`、`.trellis/spec/**` 或当前任务目录；没有修改 `async-task-guidelines.md`。

## 风险点

| 风险 | 处理方式 |
| --- | --- |
| 矩阵误述现有代码 | 以模型、生命周期函数和已有测试为准；对未在函数内校验的约束明确标记。 |
| 多表流程被简化为一张全局表 | Request、WorkItem、Attempt、Report、Delivery 分表，并在副作用列写协调关系。 |
| 新规则与数据库/目录规范重复或矛盾 | 状态规则只定义迁移设计；数据库和目录规范使用交叉引用保留自身所有权。 |
| 与活跃 scheduler 规范任务冲突 | 不编辑 `async-task-guidelines.md`，将其所有权限制保留在方案文档。 |

## 批准前检查

- [ ] `prd.md`、`design.md`、`implement.md` 和 `deferred-iterations.md` 已完成且无阻塞问题。
- [ ] `implement.jsonl` 与 `check.jsonl` 含真实的 spec/research 清单条目。
- [ ] 最新规划摘要已发送，并获得后续明确的启动批准。
