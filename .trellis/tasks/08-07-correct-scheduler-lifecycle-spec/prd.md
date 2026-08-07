# Correct Scheduler Lifecycle Spec

## Goal

Correct the scheduler lifecycle specification so every responsibility and
terminal persistence API matches the current implementation.

## Confirmed Findings

- **F-002 (P1):** `.trellis/spec/backend/async-task-guidelines.md:208-225`
  assigns scheduler scanning and execution to `tasks.py` and calls the removed
  `run_lifecycle.finish_run(...)` API.
- `backend/app/modules/scheduler/tasks.py` now owns Celery task-name
  registration.
- `backend/app/modules/scheduler/orchestration.py:42-230` owns due-job
  scanning, dispatch, execution phases, and cleanup.
- `backend/app/modules/scheduler/execution.py:20-69` executes frozen work and
  returns `SchedulerRunOutcome`.
- `backend/app/modules/scheduler/run_lifecycle.py:176-194` owns the terminal
  persistent transition through `finish_outcome(...)`.
- `backend/app/modules/scheduler/scheduler_alerts.py` owns job-alert and
  outbox state.

## Requirements

1. Revalidate the scheduler ownership split against current source before
   editing. Use CodeGraph first for source understanding.
2. Remove the obsolete `finish_run(...)` example and the claim that `tasks.py`
   owns scanning or execution orchestration.
3. Document the actual five-part contract: Celery registration, orchestration,
   pure execution outcome construction, lifecycle persistence, and
   job-alert/outbox handling.
4. State that only `run_lifecycle.py` changes `SchedulerRun` lifecycle fields,
   and that its terminal transition receives a `SchedulerRunOutcome` through
   `finish_outcome(...)`.
5. Keep the existing at-least-once, idempotency, durable state, and outbox
   invariants intact; this task corrects ownership wording only.

## Acceptance Criteria

- [ ] No active scheduler scenario assigns scanning or execution orchestration
      to `tasks.py` or references `finish_run(...)`.
- [ ] The active guidance names the five current ownership areas and their
      matching modules without duplicating low-level implementation details in
      unrelated guidance.
- [ ] Lifecycle persistence correctly names
      `run_lifecycle.finish_outcome(SchedulerRunOutcome)` as the terminal
      transition and identifies it as the owner of `SchedulerRun` lifecycle
      field changes.
- [ ] Existing Celery reliability and outbox rules remain unchanged except for
      required cross-references.
- [ ] `python .trellis/scripts/spec_wiki.py lint`, a path-scoped stale-term
      search, `python .trellis/scripts/task.py validate <task-dir>`, and
      `git diff --check` pass.

## Scope

In scope:

- The scheduler scenario in `.trellis/spec/backend/async-task-guidelines.md`
  and any index or cross-reference required for F-002.
- This task's planning artifacts and the parent integration record.

Out of scope:

- Changes under `backend/app/modules/scheduler/**` or any other product source,
  tests, generated clients, database schema, dependencies, migrations, or
  runtime configuration.
- Reorganizing the large async guide solely for length; that governance work is
  owned by the remaining-findings child task and must preserve this corrected
  contract.

## Open Questions

None. The audit evidence identifies both the stale claims and the current
ownership contract.
