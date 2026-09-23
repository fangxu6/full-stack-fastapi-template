# Architecture Decision Documentation Consolidation

## Boundary

The repository will have two Trellis-owned decision layers:

1. `.trellis/spec/**` contains the current, executable engineering contracts
   that should be read before implementation.
2. `.trellis/tasks/**` contains task-scoped requirements, trade-offs, research,
   implementation decisions, and archived historical records.

`docs/adr/**` and `docs/decisions/**` are redundant stores and will be removed.
Git history remains the recovery mechanism for the deleted files.

## Migration Mapping

- Frontend component adoption: `.trellis/spec/frontend/component-guidelines.md`
  and its quality guidance.
- Backend module boundaries, database identity, transactions, and audit actor:
  `.trellis/spec/backend/{directory-structure,database-guidelines,type-safety}.md`.
- Celery, Redis, email outbox, scheduler lifecycle, and task observability:
  `.trellis/spec/backend/{async-task-guidelines,event-callback-guidelines,state-transition-guidelines,logging-guidelines}.md`.
- Retired AI inventory capability and deferred external ERP API: the existing
  archived Trellis tasks plus `.trellis/spec/log.md` where the current-state
  retirement is recorded.
- Historical status, supersession, and alternatives: existing archived tasks,
  especially the ADR review and feature-specific tasks. Do not create a new
  parallel ADR index.

## Link Migration

Search all retained files, including archived task artifacts, for:

- literal `docs/adr` and `docs/decisions` paths;
- Markdown links into those directories;
- skill instructions that prescribe the deleted workflow.

Replace each reference with the owning spec or Trellis task path. Where an
historical ADR number is useful for context but no longer has a file target,
retain the plain historical label without a broken Markdown link.

The `domain-modeling` skill becomes Trellis-compatible: it records a decision
in the current task first and promotes a durable current rule to `.trellis/spec`.
It must not prescribe a deleted `docs/adr` directory.

## Compatibility And Rollback

- No application behavior changes, so no runtime migration or API compatibility
  work is needed.
- If validation finds a decision not represented in Trellis, restore only that
  decision's content into the owning spec/task artifact before deleting the
  source directory.
- The deletion is recoverable from Git history; no destructive filesystem
  command is required.

## Review Boundary

The final review must distinguish this task's staged files from the existing
`.claude/**` deletions. The latter are user-owned unrelated changes and must not
be included in this task's commit.
