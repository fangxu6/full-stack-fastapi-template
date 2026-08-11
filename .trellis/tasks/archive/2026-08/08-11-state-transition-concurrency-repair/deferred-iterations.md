# State Transition Concurrency Repair Deferred Iterations

## Purpose

This task closes the daily-report stale-result and scheduler cancel/claim
boundaries without expanding into scheduler execution-result ownership.

## Traceability Rules

- Deferred items do not affect this task's acceptance criteria.
- Each item requires an independent Trellis task before implementation.
- A future design must preserve the existing scheduler worker commit phases.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Fence `finish_outcome()` against stale or terminal worker results. | The current outcome carries no attempt or lease identity, so adding a guard requires a scheduler compatibility and at-least-once delivery design rather than a cancel-query change. | Scheduler lifecycle design and worker context contract. | PRD, concurrency design, focused lifecycle tests, matrix update. |

## Remaining Work In Current Scope

Implement and test lease-matched daily-report result handling, row-locked
scheduler cancellation, the matching matrix corrections, and session-history
repair.
