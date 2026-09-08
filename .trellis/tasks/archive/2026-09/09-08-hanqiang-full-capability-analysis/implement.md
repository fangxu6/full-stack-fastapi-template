# 执行计划：Hanqiang 全量能力分析与 prod 文档

## 顺序清单

1. [x] 汇总并审阅后端 59 个提交文件的研究报告，确认每个文件都有映射。
2. [x] 汇总并审阅前端 39 个提交文件的研究报告，确认每个文件都有映射。
3. [x] 汇总 7 个非提交指南、现有评估报告和索引差异，确定最终能力 taxonomy。
4. [x] 创建全量能力矩阵，逐行覆盖 98 个提交文件，并为每行提供来源链接、决策和 prod 文档链接。
5. [x] 创建 `prod/` 索引和每项能力的 prod 文档；将“复用现有”和“暂缓”也写出边界，避免误认为已实现。
6. [x] 更新 `docs/hanqiang-platform-capability-assessment.md`，补充全量分析结论、能力差距、分期、入口链接和不复制清单。
7. [x] 更新 `docs/hanqiang-core-contributions.md` 的统计、遗漏链接、能力分组和 prod 文档入口。
8. [x] 运行链接/覆盖/Markdown 质量检查，复查工作区只包含本任务文档变更。

## 预期文件

- `docs/hanqiang-core-contributions/capability-matrix.md`
- `docs/hanqiang-core-contributions/prod/index.md`
- `docs/hanqiang-core-contributions/prod/prod-*.md`
- `docs/hanqiang-platform-capability-assessment.md`
- `docs/hanqiang-core-contributions.md`

## 验证命令

- `python3 ./.trellis/scripts/task.py validate 09-08-hanqiang-full-capability-analysis`
- 用 `rg --files` 重新统计提交文件，并与矩阵中 98 个唯一文件名比对。
- 用 `rg -o` 校验矩阵中的提交级相对链接和 prod 索引链接。
- 检查 Markdown 标题层级、空链接、重复映射、未引用来源和敏感值。
- 由于无运行时代码、API、数据库迁移或前端生成文件，不运行前后端测试；在最终报告中说明原因。

## 风险与回滚

- 风险：总索引历史计数与目录实际文件数不一致。缓解：以实际文件清单和自动覆盖检查为准。
- 风险：将单一业务页面误升格为平台能力。缓解：矩阵必须记录跨域消费者、所有权和模板差距。
- 风险：历史缺陷被写成生产方案。缓解：每份 prod 文档单列“禁止复制行为”和来源。
- 回滚：本任务所有变更均为 Markdown；按文件回退本任务提交即可，不涉及数据或运行时回滚。
