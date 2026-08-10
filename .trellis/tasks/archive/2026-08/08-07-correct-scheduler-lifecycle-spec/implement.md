# Implementation Plan: Correct Scheduler Lifecycle Spec

## 1. Revalidate Before Editing

- Use CodeGraph to confirm `tasks.py` registers Celery names, while
  `orchestration.py`, `execution.py`, `run_lifecycle.py`, and
  `scheduler_alerts.py` retain the ownership recorded in `prd.md`.
- Read ADR-0012 and the current Scheduler Run Lifecycle Ownership scenario.
- Confirm that this remains a documentation-only child task of
  `08-07-refresh-trellis-spec-architecture`.

## 2. Correct the Active Scenario

- Edit only the Scheduler Run Lifecycle Ownership section in
  `.trellis/spec/backend/async-task-guidelines.md`.
- Replace `tasks.py` scanning/execution language with its thin-adapter role:
  compatibility export plus Celery registration, with `orchestration.py` as
  the owner of scheduling coordination.
- State the five-part owner table in concise prose; keep detailed implementation
  mechanics in source instead of copying them into unrelated guide sections.
- Replace `finish_run(...)` with the actual
  `execution.execute(...) -> SchedulerRunOutcome -> finish_outcome(...)`
  sequence.
- Preserve all existing at-least-once, lease, transaction, and outbox rules.

## 3. Review Scope Boundaries

- Do not edit `backend/app/modules/scheduler/**`, tests, migrations, configs,
  generated clients, or ADR-0012 unless current source disproves it.
- Do not reorganize the full async guide; leave that independent governance
  work to `08-07-refresh-frontend-and-guide-spec-contracts`.
- Do not create an API E2E plan or start services because no runtime contract
  changes.

## 4. Validate

Run from the repository root:

```powershell
rg -n "finish_run" .trellis/spec docs/adr
rg -n "tasks\.py|orchestration\.py|finish_outcome|SchedulerRunOutcome" .trellis/spec/backend/async-task-guidelines.md
python .trellis/scripts/spec_wiki.py lint
python .trellis/scripts/task.py validate .trellis/tasks/08-07-correct-scheduler-lifecycle-spec
git diff --check
git diff --cached --check
```

Then review the final diff against ADR-0012 and the five source owners. The
`finish_run` search must return no active scheduler-guidance match; inspect the
ownership-name search to confirm it describes the thin adapter rather than a
former `tasks.py` orchestration role.

## Rollback Point

Revert only the async-guide scenario if its wording is found to conflict with
current source. Keep this task's evidence and planning artifacts so the parent
integration task can re-evaluate the correction.

## Completion Gate

- The PRD, design, and implementation plan agree on the five ownership areas
  and the documentation-only boundary.
- `implement.jsonl` and `check.jsonl` contain real specification/research
  entries rather than seed examples.
- The user reviews this final plan before `task.py start`; approval to plan is
  not approval to edit the active specification.
