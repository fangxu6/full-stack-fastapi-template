# 合并分析：Trellis v0.6.17 工作流

## 来源比较

- `.trellis/workflow.md`：763 行，升级前的本地工作流。
- `.trellis/workflow.md.new`：721 行，升级到 v0.6.17 后的候选工作流。
- `.trellis/.gitignore` 忽略 `*.new`，因此候选文件是 sidecar 输入，不会被跟踪。

## 需要保留的候选新增内容

1. `task_error` 出现在状态范围说明中，并拥有匹配的面包屑区块。现有 `.codex/hooks/inject-workflow-state.py` 已经会在活动任务记录缺失、格式错误或缺少可用 status 时返回 `task_error`。
2. Task 章节说明 seed 为空的 `implement.jsonl` / `check.jsonl` manifest 属于规划错误，并记录了 `task.py start --allow-empty-context`。现有 `.trellis/scripts/task.py` 已实现对应 gate 和参数。
3. `DeepSeek Harness` 被加入 inline/class-2 平台范围。现有 `.trellis/scripts/common/workflow_phase.py` 将 `dsh` 映射为 `DeepSeek Harness`，平台映射文档也说明了它的 inline 工作流行为。

## 需要恢复的本地策略

以下差异由本地历史和测试支持，并不是偶然遗留的旧文案：

- `c0044fc` 增加了 E2E 规划/验证、`grill-with-docs` 和复杂任务规划保护。
- `006da42` 增加了 deferred-iterations 指引。
- `12ad458` 将本地 E2E 设置改为明确的 isolated environment，并移除了 Docker Compose 假设。
- `31926e3` 增加了生成前端产物同步和提交批次处理。
- `.trellis/tests/test_spec_wiki.py` 要求存在 `e2e-api-tests.md`、`grill-with-docs`、`spec_wiki.py index/lint/log`、后端 health endpoint、前端 endpoint 和 isolated-environment 表述，同时拒绝 `Docker Compose`。

## 合并结论

最终工作流应当是 v0.6.17 运行时/平台新增内容与本仓库本地策略的并集。直接用 `.new` 替换当前文件虽然符合上游形态，但会导致本地工作流一致性测试失败，并删除有意设置的项目保护。更新模板哈希还会掩盖最终工作流已经本地定制这一事实，因此必须保持哈希文件不变。
