# Business workflow platform

## Goal

D-007: derive a reusable cross-role workflow design from a completed, concrete
inventory business process before selecting generic runtime mechanics.

## Confirmed Context

- No current module provides a generic approval, work-item, state-transition,
  timeout, or retry workflow capability.
- D-003 supplies durable operation audit, and D-004 supplies managed scheduled
  execution; this task must consume those capabilities rather than replace
  them.
- [Inventory exception correction](../08-04-inventory-exception-correction/)
  is the first product workflow because inventory is the only current business
  domain. Its completion is a prerequisite for this task to continue beyond
  planning.

## Requirements

- Do not select a generic workflow runtime, define reusable workflow tables,
  or start D-007 implementation until the inventory-exception-correction child
  task is archived as completed.
- After the child completes, use its proven trigger, roles, state transitions,
  work-item lifecycle, timing rules, and audit evidence as D-007's first
  workflow contract.
- Decide whether an approval is a reusable workflow primitive only after the
  completed inventory process demonstrates that its approval decision cannot
  remain domain-specific.

## Acceptance Criteria

- [ ] `08-04-inventory-exception-correction` is archived as completed with a
  reviewed product contract, implementation evidence, migration/rollback
  outcome, and end-to-end validation result.
- [ ] D-007's PRD records the completed child workflow's states, role actions,
  exceptions, timing rules, and domain-specific versus reusable boundaries.
- [ ] D-007 design, implementation plan, migration/rollback plan, and API/UI
  test scope are reviewed after the child-completion gate, before
  `task.py start`.

## Out of Scope

- Building a generic workflow engine, approval runtime, or work-item UI before
  the inventory-exception-correction child task completes.
