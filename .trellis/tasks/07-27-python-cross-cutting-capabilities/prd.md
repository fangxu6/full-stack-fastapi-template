# Python 横切能力改造

## Goal

按已记录的 ADR 废止服务层事务边界，删除 AI 库存查询，引入请求级 Unit of Work、显式审计 Actor、通用邮件发件箱与安全的 Celery 任务观测上下文；仅在评审通过后实施。

## Requirements

- TBD

## Acceptance Criteria

- [ ] TBD

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
