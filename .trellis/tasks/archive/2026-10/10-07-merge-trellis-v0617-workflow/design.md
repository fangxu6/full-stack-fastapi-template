# 设计：合并 Trellis v0.6.17 工作流

## 1. 范围与归属

本次唯一涉及的产品文件是 `.trellis/workflow.md`。`.trellis/workflow.md.new` 是被忽略的升级 sidecar，保持不变。合并不能修改消费 workflow-state 标签的运行时脚本，也不能修改保护本地工作流一致性的测试。

## 2. 合并模型

以 v0.6.17 候选文件作为结构基线，再在对应的语义位置恢复本仓库的本地改动。这是语义合并，不是盲目覆盖，因为候选文件有意删除了若干本地策略。

优先级规则：

1. 对新增状态和平台行为，以候选文件的运行时兼容性为准：保留 `task_error`、空 context 指引、`--allow-empty-context` 和 `DeepSeek Harness` 范围。
2. 对本仓库明确引入并由测试保护的规则，以本地策略为准：保留 E2E 规划/验证、`grill-with-docs`、deferred iterations、spec wiki 维护、isolated-environment 表述和生成前端产物提交处理。
3. 对共有说明，采用候选文件较新的表述，并在对应章节只插入一次本地补充内容。
4. 解析器契约优先于文字简洁性：所有状态和平台区块必须保留严格匹配的开闭标签。

## 3. 章节映射

| 工作流区域 | 候选文件的变化 | 合并动作 |
| --- | --- | --- |
| Spec 系统 | 删除 `spec_wiki.py` 命令 | 保留本地 index/lint 命令，因为脚本和一致性测试都存在。 |
| Task 系统 | 说明 seed 为空的 manifest 和 `--allow-empty-context` | 采用候选文件内容。 |
| 状态契约 / Phase Index | 新增 `task_error`，简化 Phase 1 摘要 | 采用 `task_error`，并将候选摘要与本地复杂计划压力测试说明合并。 |
| 规划产物 | 删除 E2E 和 deferred guidance | 恢复本地两项要求。 |
| 规划面包屑/路由 | 删除 `grill-with-docs`，向 inline 范围新增 DeepSeek | 保留本地评审路由，并把 DeepSeek 加入候选范围。 |
| Phase 2 上下文/检查 | 删除 E2E 上下文和执行检查 | 保留候选流程，并恢复 E2E 上下文和检查引用。 |
| Phase 3.3 | 删除 spec wiki 维护 | 恢复本地 catalog/log/lint 命令。 |
| Phase 3.4 | 删除生成产物批处理 | 恢复本地生成前端产物同步和提交编号规则。 |
| 本地 E2E 验证 | 候选文件删除该章节 | 恢复现有 endpoint 和 isolated-environment 表述。 |

## 4. 契约与兼容性

- Python/OpenCode workflow-state 注入器会从 `.trellis/workflow.md` 解析状态区块，因此必须继续保留所有必要状态区块及匹配的开闭标签。
- `task.py` 已经实现候选文件中的空 context gate，因此候选文件的说明与当前运行时兼容。
- 本地测试明确要求 E2E、`grill-with-docs`、spec wiki、health endpoint、frontend endpoint 和 isolated-environment 表述，并拒绝 `Docker Compose` 表述。合并结果必须满足这些断言。
- `.trellis/.template-hashes.json` 是管理状态文件。本地合并后的工作流属于用户定制内容，因此有意不修改该文件。

## 5. 验证与回滚

使用空白检查、现有 `.trellis/tests` 测试和状态/平台开闭标签结构扫描验证最终文件。将最终 diff 分别与两个来源文件比较，确认产品文件中只有目标工作流发生预期变化。编辑前，当前文件和被忽略的 sidecar 都仍可恢复；如果合并失败，可以恢复编辑前的 `.trellis/workflow.md`，再按章节映射重新合并。
