# 合并 Trellis v0.6.17 工作流

## 目标

将升级前的 `.trellis/workflow.md` 与 v0.6.17 候选文件 `.trellis/workflow.md.new` 合并，使受版本升级影响的运行时规则进入正式工作流，同时保留本仓库已经验证过的本地工作流策略。

## 背景

- `.trellis/workflow.md` 是本地工作流的事实来源，负责阶段说明、workflow-state 面包屑、平台路由、任务产物以及收尾/提交规则。
- `.trellis/workflow.md.new` 是升级到 v0.6.17 后生成的候选文件。`.trellis/.gitignore` 通过 `*.new` 忽略它，因此它只是本次比较的输入，不是最终要提交的文件。
- 候选文件新增了 `task_error` 工作流状态、seed 为空的 context manifest 说明及 `task.py start --allow-empty-context`，并把 `DeepSeek Harness` 加入 inline/class-2 平台范围。
- 当前文件包含本仓库通过提交 `c0044fc`、`006da42`、`12ad458` 和 `31926e3` 增加的本地策略：`e2e-api-tests.md` 规划与验证、`grill-with-docs` 评审路由、deferred iterations 指引、spec wiki 维护、明确的 isolated-environment 表述，以及生成前端产物的提交处理规则。
- `.trellis/tests/test_spec_wiki.py` 会检查本地 E2E、规划评审、spec wiki 和 isolated-environment 相关工作流文本。当前 `task.py` 已支持候选文件中的空 context 检查和 `--allow-empty-context` 参数。
- `.trellis/.template-hashes.json` 已记录 `.trellis/workflow.md` 的 Trellis 模板基线。不能手工重写该文件；合并后的本地工作流应继续被未来升级识别为本地定制文件。

## 需求

1. 以 `.trellis/workflow.md.new` 作为 v0.6.17 上游变更的结构和平台列表基线。
2. 保留候选文件中兼容当前运行时的新增内容：
   - `workflow-state:task_error` 契约及其面包屑区块。
   - 对空的 `implement.jsonl` / `check.jsonl` manifest 的提示，以及 `--allow-empty-context` 例外参数。
   - 在所有对应的 inline/class-2 路由和执行范围中加入 `DeepSeek Harness`。
3. 恢复并同步候选文件删除或缩短的本地策略：
   - `spec_wiki.py index`、`spec_wiki.py lint` 以及 Phase 3.3 的 catalog/log 维护流程。
   - 将 `e2e-api-tests.md` 作为 API/跨层复杂任务的规划产物、上下文输入和质量验证路径。
   - 对复杂或高风险工作保留 `grill-with-docs` 路由和规划说明。
   - 对已确认存在延后范围的大型任务保留 deferred-iterations 指引。
   - 保留明确的 isolated-environment 验证表述，不重新引入 Docker Compose 假设。
   - 保留生成前端产物的同步和提交批次规则。
4. 保持 workflow-state 开闭标签成对、平台区块符合解析器要求，并避免合并后出现重复或相互矛盾的说明。
5. 产品文件范围仅限 `.trellis/workflow.md`；不得修改 `.trellis/workflow.md.new`、脚本、测试、模板哈希或其他未提交文件。

## 验收标准

- [ ] `.trellis/workflow.md` 包含 v0.6.17 的 `task_error`、空 context 和 `DeepSeek Harness` 行为。
- [ ] `.trellis/workflow.md` 保留 `.trellis/tests/test_spec_wiki.py` 中 `WorkflowParityTests` 所要求的全部本地策略。
- [ ] 每个 workflow-state 区块的开闭标签匹配，每个平台列表区块也保持结构成对。
- [ ] 合并后的文档没有由两个来源造成的重复章节或相互矛盾指令。
- [ ] `python3 -m unittest discover -s .trellis/tests` 通过，且 `git diff --check` 不报告空白错误。
- [ ] `.trellis/workflow.md.new` 和其他无关改动保持不变；不手工更新 `.trellis/.template-hashes.json`。

## 范围外

- 不更新 Trellis 脚本、hooks、平台 agents、skills 或 commands 的运行时行为。
- 不处理本次合并之外的既有文档引用问题，包括当前工作流引用但仓库中不存在的 workflow contract 路径。
- 不更新 Trellis CLI 版本，不重新生成全部模板文件，也不删除被忽略的 `.new` 比较文件。
- 不提交或修改无关的任务归档目录。

## 关键决策

- 采用并集式合并：先保留 v0.6.17 的结构和运行时新增内容，再保留候选文件删除但本仓库测试和历史提交明确要求的本地策略。
- 将 `.new` 视为只读输入快照，交付物是现有的 `.trellis/workflow.md`。
- 保持现有模板哈希基线不变，使未来 Trellis 更新仍能识别本地工作流定制。

## 风险与延后事项

- 最终工作流会因为本仓库的规划和验证要求而有意不同于标准 v0.6.17 候选文件。未来升级仍需重复 sidecar 比较流程。
- 当前工作流引用 `.trellis/spec/cli/backend/workflow-state-contract.md`，但该路径不在当前仓库中。修复这一既有引用属于延后事项，不纳入本次合并。

## 阻塞性待决问题

无。目标是合并正式工作流，仓库证据已经明确了需要保留和采用的内容。
