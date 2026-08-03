# Business workflow platform

## Goal

D-007: plan the first approved cross-role business workflow before selecting
generic runtime mechanics.

## Confirmed Context

- No current module provides a generic approval, work-item, state-transition,
  timeout, or retry workflow capability.
- D-003 supplies durable operation audit, and D-004 supplies managed scheduled
  execution; this task must consume those capabilities rather than replace
  them.

## Requirements

- Product owner identifies one concrete cross-role process, its roles,
  decisions, hand-offs, service-level timing, and success conditions.
- Define the process state machine, assignments, approvals, timeout/retry
  behavior, work-item API/UI, and audit integration from that process first.
- Select a workflow runtime only after the process contract is approved.

## Acceptance Criteria

- [ ] Product owner approves a first cross-role process with testable end-to-end
  acceptance criteria.
- [ ] PRD contains the process states, role actions, exceptions, and timing
  requirements that drive the design.
- [ ] Design, implementation plan, migration/rollback plan, and API/UI test
  scope are reviewed before `task.py start`.

## Out of Scope

- Building a generic workflow engine without an approved business process.
