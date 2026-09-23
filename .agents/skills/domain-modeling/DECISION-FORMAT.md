# Trellis Decision Format

Record decisions in the current Trellis task, not in a separate decision
directory.

## Task Record

Use `prd.md` for requirements, constraints, and acceptance criteria. Use
`design.md` for the decision, alternatives, consequences, compatibility, and
rollback considerations. The task is the durable historical record after it is
archived under `.trellis/tasks/archive/`.

## Current Contract

When a decision establishes a rule that future implementation must follow,
promote the concise executable contract to the owning `.trellis/spec/` file and
append the change to `.trellis/spec/log.md`.

## Decision Checklist

Record a durable decision when it is hard to reverse, surprising without
context, and the result of a real trade-off. For ordinary implementation
choices, keep the reasoning in the task artifact and do not create a separate
decision document.
