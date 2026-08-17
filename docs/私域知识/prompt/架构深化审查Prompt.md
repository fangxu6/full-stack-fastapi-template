# 架构深化审查 Prompt 模板

用于调用 `$improve-codebase-architecture`。目标是识别当前仍存在的架构摩擦，不重复报告已经由后续提交解决的问题。

## 使用方式

先完成代码提交并确认工作区干净：

```bash
rtk git status --short
rtk git rev-parse HEAD
rtk git log --oneline -12
```

将下面的模板紧跟在 `$improve-codebase-architecture` 后发送，并替换所有 `{{...}}` 占位符。

## 调用模板

```text
请以当前 HEAD {{HEAD_SHA}} 为唯一分析基线，执行本次架构深化审查。

本次范围是 report-only：
- 不创建 Trellis 任务；
- 不修改源代码、测试、迁移或项目文档；
- 先生成架构候选报告，不进入 grilling，也不开始实现。

历史上下文：
- 上一次架构报告：{{PREVIOUS_REPORT_PATH}}
- 本次已完成的修复提交：{{COMPLETED_COMMITS}}
- 相关已归档任务：{{ARCHIVED_TASK_PATHS}}

请先读取并遵守：
- CONTEXT.md
- 与候选模块相关的 docs/adr/
- 相关 .trellis/tasks/archive/ 任务记录
- 与候选模块相关的当前源码、调用方和测试检索结果

请按以下顺序工作：

1. 确认当前 HEAD、工作区状态和最近提交，所有结论必须针对当前 HEAD。
2. 读取历史报告和已完成提交，建立候选的历史状态。
3. 重点扫描最近变更热点，但不要把“最近修改过”直接判定为“仍未解决”。
4. 对每个候选追踪当前调用路径、当前实现和测试，不只依据文件长度、文件名或历史报告措辞。
5. 应用 deletion test，判断删除该 module 是否真的会集中复杂度，而不是简单移动复杂度。
6. 对历史候选逐项分类：
   - resolved：原问题已由当前代码或后续提交解决；
   - partially-resolved：原问题已缩小，但仍有明确未完成的 seam；
   - still-open：当前代码仍满足原 Problem 描述；
   - false-positive：原描述不再适用于当前代码，或属于有意保留的局部状态；
   - new：历史报告中没有的新问题。
7. resolved 和 false-positive 不得作为本次推荐候选；partially-resolved 必须明确说明它不是原问题的简单重复。
8. 每个保留候选必须给出当前文件路径、行号、调用方、测试证据和与历史候选的关系。
9. 如果没有新的高价值候选，明确输出“当前没有可操作的架构深化候选”，不要为了满足 Top recommendation 强行提出重构。

报告至少包含：
- 当前 HEAD SHA 和报告时间；
- 历史候选状态表；
- 当前仍开放或部分完成的候选；
- 每个候选的 Problem、Solution、Benefits、Before/After 和 ADR 影响；
- 明确标注 stale、partial、open、new，不要把历史问题写成当前问题。

生成报告后，先不要让我选择候选。先输出一份“候选复核表”，逐项说明：
- 当前代码是否仍符合 Problem 描述；
- 哪个提交解决或改变了该问题；
- 它是原问题、下一层 seam，还是误报；
- 是否建议进入 grilling。
```

## 报告后的选择规则

只从 `still-open` 或确有价值的 `partially-resolved` 候选中选择进入 grilling。

如果报告再次出现已经完成的候选，先要求重新核验当前 HEAD 和修复提交，不要直接开始实现。

报告应保留在 skill 规定的操作系统临时目录；本目录只保存本 Prompt 模板，不保存每次生成的 HTML 报告。
