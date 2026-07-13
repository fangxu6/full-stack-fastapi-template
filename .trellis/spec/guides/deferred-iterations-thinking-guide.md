# Deferred Iterations Thinking Guide

> Preserve confirmed future work without letting it silently expand the current
> task's acceptance criteria.

## When To Use

Use this guide while planning a major task when all of the following are true:

- the current request contains several business flows or independently valuable
  deliverables;
- one or more deliverables are explicitly confirmed as out of scope for the
  current iteration; and
- their dependencies or future acceptance conditions need to remain visible.

Do not create this file for ordinary TODOs, defects found during implementation,
or work that is still required for the current task to meet its acceptance
criteria.

## Choose The Right Place

| Situation | Record it in |
|---|---|
| Deliverable must be implemented and verified in the current initiative | A child task, with its dependency order in the child's `prd.md` and `implement.md`. |
| Deliverable is explicitly deferred to a later iteration | `<task>/deferred-iterations.md`. |
| Small follow-up with no dependency or scope boundary | The current task's `prd.md` backlog or a new small task. |
| Failed current acceptance criterion | The current task's PRD, design, implement plan, and debugging record. |

`deferred-iterations.md` is a scope and traceability register. It is not a
substitute for a future task's `prd.md`, `design.md`, `implement.md`, or
validation plan.

## Recommended Structure

Create `<task>/deferred-iterations.md` with these sections when the guide
applies:

```md
# <Feature> Deferred Iterations

## Purpose

State the current delivery boundary and why deferred work is tracked here.

## Traceability Rules

- Deferred items do not fail the current task's acceptance criteria.
- Each item needs an independent task before implementation.
- Dependencies must be satisfied before a dependent item is started.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
|---|---|---|---|---|
| D-001 | <scope> | <why deferred> | <task IDs or domain dependencies> | <PRD/design/API/tests> |

## Suggested Iteration Order

Order the deferred items only where a real dependency exists.

## Carry-Forward Acceptance Notes

List preconditions that must be resolved before a future item can be planned or accepted.

## Remaining Work In Current Scope

Keep unfinished current acceptance work separate from deferred work, with its blocker and next action.
```

Use stable `D-001` style IDs. A dependency may name a future item ID, an
existing task, or a concrete domain prerequisite. Do not express dependencies
only by the table's visual order.

## Planning Rules

- Link the register from the current task's `prd.md`, `design.md`, and
  `implement.md` when it changes the delivery boundary.
- Keep the current task's acceptance criteria limited to its confirmed scope.
- Before starting a deferred item, create an independent task and write its own
  requirements, technical design, implementation plan, and proportionate test
  plan. API-facing or cross-layer work also follows the repository E2E planning
  requirement.
- Do not expose unfinished deferred workflows through placeholder controls,
  permissive fallbacks, or unverified synthetic data.
- Update the register when a deferred item is promoted, split, superseded, or
  found to depend on a newly discovered prerequisite.

## Review Checklist

- [ ] Every deferred item is explicitly outside the current acceptance criteria.
- [ ] Each item has a reason, dependencies, and expected future deliverables.
- [ ] Current-scope unfinished work is not mixed into the deferred-item table.
- [ ] The iteration order reflects real dependencies rather than wishful sequencing.
- [ ] No deferred workflow is partially exposed as a production feature.
