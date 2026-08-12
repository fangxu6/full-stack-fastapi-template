# Implementation Plan: Workflow Capability YAGNI Audit

## Gate

This task remains planning-only until the final planning summary is approved.
Do not run `task.py start` or change product source from these artifacts.

## Ordered Checklist

1. Revalidate the archived inventory correction contract and its source/test
   anchors; keep the handoff note in `research/` current.
2. If a second workflow is approved, document its domain-local state matrices,
   roles, side effects, lease/retry/recovery semantics, audit rules, API/UI
   behavior, and operational ownership before comparing it with inventory.
3. Build a field/transition comparison: common mechanics, domain extensions,
   incompatible semantics, and the smallest shared seam, if any.
4. Choose one of two outcomes: retain two domain-local implementations, or
   open a new implementation task for a narrowly scoped shared mechanic. A
   runtime/library selection is allowed only in the latter task.
5. For a shared mechanic, define additive schema/API migration, generated
   client impact, backfill or dual-write requirements, downgrade limits, and a
   rollback that leaves inventory correct if promotion is interrupted.
6. Add focused unit/integration tests for both workflows, then execute the
   comparison E2E cases in `e2e-api-tests.md` against an isolated environment.
7. Run the relevant backend/frontend quality gates, generated-client sync when
   contracts change, and `git diff --check` before any implementation commit.

## Current Validation

- `python .trellis/scripts/task.py validate .trellis/tasks/08-03-business-workflow-platform`
- `python .trellis/scripts/spec_wiki.py lint`
- `git diff --check`
- Product tests are not rerun by this planning task; the archived child
  records its 322-test isolated backend result and process-level blockers.

## Future Migration / Rollback Gate

No migration is planned now. A future promotion task must include named tables,
constraints, enum evolution, generated-client changes, downgrade behavior, and
an interruption test proving that an in-flight inventory correction cannot be
duplicated or lose its audit/ledger outcome.
