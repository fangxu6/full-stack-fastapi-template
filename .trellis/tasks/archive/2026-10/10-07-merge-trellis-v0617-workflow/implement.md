# 执行计划：合并 Trellis v0.6.17 工作流

## 有序清单

1. 编辑前重新阅读 `prd.md`、`design.md`、当前工作流和 `.new` 候选文件。
2. 以 `.new` 候选文件为基础，根据设计中的章节映射恢复本地章节和规则。
3. 检查每个 `[workflow-state:*]` 区块和平台列表区块，确认开闭标签严格匹配，必需步骤的说明保持同步。
4. 分别对比两个来源文件检查 diff。确认产品文件中只有 `.trellis/workflow.md` 被修改；`.new`、模板哈希和无关任务归档保持不变。
5. 执行下面列出的质量检查，发现文档或解析问题时修复后重跑。
6. 在任务材料中记录最终验证结果，然后请求实施/提交评审门禁。

## 验证命令

```bash
python3 -m unittest discover -s .trellis/tests
python3 - <<'PY'
from pathlib import Path
import re
text = Path('.trellis/workflow.md').read_text(encoding='utf-8')
statuses = re.findall(r'^\[workflow-state:([A-Za-z0-9_-]+)\]$', text, re.MULTILINE)
for status in statuses:
    assert text.count(f'[workflow-state:{status}]') == 1
    assert text.count(f'[/workflow-state:{status}]') == 1
assert 'DeepSeek Harness' in text
assert '[workflow-state:task_error]' in text
assert '--allow-empty-context' in text
print(f'validated {len(statuses)} workflow-state blocks')
PY
git diff --check
git diff -- .trellis/workflow.md
```

## 风险点与回滚

- 最高风险是采用 v0.6.17 的精简表述时无意丢失本地规划/验证策略。接受 diff 前必须逐项对照本地测试要求检查被删除的内容。
- 第二个风险是 workflow-state 或平台列表开闭标签不匹配，导致 hook 静默忽略区块。使用结构扫描和现有测试防止该问题。
- 不更新 `.trellis/.template-hashes.json`；保持其不变是有意的管理策略。
- 不暂存 `.trellis/workflow.md.new` 或无关的任务归档目录。

## 启动前评审门禁

- `prd.md`、`design.md` 和本 `implement.md` 已完成。
- `implement.jsonl` 和 `check.jsonl` 已包含工作流定制规范与合并研究记录。
- 这是文档任务，不需要产品代码或 API E2E 运行环境。

## 最终验证结果

- `python3 -m unittest discover -s .trellis/tests`：通过，5 个测试全部通过。
- workflow-state 和平台区块结构扫描：通过，8 组 workflow-state 开闭标签匹配；`task_error`、`--allow-empty-context`、`DeepSeek Harness` 及本地策略标记均存在，且没有 `Docker Compose` 文案。
- `git diff --check -- .trellis/workflow.md`：通过。
- `git diff --name-only HEAD`：仅包含 `.trellis/workflow.md`；`.new`、模板哈希和无关任务归档未修改。
- `trellis-implement` 子代理因运行环境缺少 Bedrock API key 未启动，已由主会话按相同规划完成实施和验证。
