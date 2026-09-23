# Journal - fx (Part 2)

> Continuation from `journal-1.md` (archived at ~2000 lines)
> Started: 2026-09-08

---



## Session 70: 完成 Hanqiang 全量能力 prod 文档拆分

**Date**: 2026-09-08
**Task**: 完成 Hanqiang 全量能力 prod 文档拆分
**Branch**: `master`

### Summary

完成 98 个提交文件的能力矩阵，拆分 15 份独立 prod 能力文档并更新索引、评估报告与复用指南；通过链接、格式和任务校验，未修改运行时代码。

### Git Commits

| Hash | Message |
|------|---------|
| `7893635` | (see git log) |

### Status

[OK] **Completed**


## Session 71: Implement event callback kernel

**Date**: 2026-09-19
**Task**: Implement event callback kernel
**Branch**: `master`

### Summary

Implemented the kernel-only event callback capability: immutable event publications, strict envelopes, code-registered handler matching, durable delivery state, dispatch and execution leases, bounded retries/recovery, AuditEvent/Actor integration, Celery scanning and real Redis/Worker verification. Added backend event callback spec and archived the Trellis task. Webhook and business adapters remain deferred.

### Git Commits

| Hash | Message |
|------|---------|
| `ef16b14` | (see git log) |

### Status

[OK] **Completed**


## Session 72: Remove LLM-Wiki and knowledge-base skills
<!-- trellis-session: v=2 fp=7911d017e40eeb66 -->

**Date**: 2026-09-23
**Task**: Remove LLM-Wiki and knowledge-base skills
**Branch**: `master`

### Summary

Removed docs/llm-wiki and the three kb-* skills, cleaned active documentation references, preserved archived history and Trellis spec tooling, and verified stale-reference search, spec lint, and git diff check.

### Git Commits

| Hash | Message |
|------|---------|
| `7e288a5` | chore: remove llm-wiki and kb skills |

### Status

[OK] **Completed**


## Session 73: Consolidate architecture decision docs
<!-- trellis-session: v=2 fp=e6c4015019b3ef96 -->

**Date**: 2026-09-23
**Task**: Consolidate architecture decision docs
**Branch**: `master`

### Summary

Removed docs/adr and docs/decisions, migrated current rules and historical decision references into Trellis specs and archived task records, updated decision-recording skill guidance, and passed spec wiki plus Trellis tests.

### Git Commits

| Hash | Message |
|------|---------|
| `bcc19e9` | docs: consolidate architecture decisions into trellis |

### Status

[OK] **Completed**
