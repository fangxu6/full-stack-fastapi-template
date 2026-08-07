# Implementation Plan: Coordinate Trellis Spec Architecture Refresh

## 1. Maintain Planning Boundaries

- Keep this parent and all three children in `planning` until their individual
  final planning summaries are reviewed and explicitly approved.
- Do not edit active `.trellis/spec/**` files from this parent. Route each
  finding to its owning child task.
- Keep the child map in `prd.md` synchronized if scope is refined or a child
  is superseded.

## 2. Execute Child-Owned Corrections

- `08-07-correct-backend-hybrid-architecture-spec` owns F-001.
- `08-07-correct-scheduler-lifecycle-spec` owns F-002.
- `08-07-refresh-frontend-and-guide-spec-contracts` owns F-003 through F-006.
- The remaining-findings child must consume F-002's final scheduler wording
  before it restructures async guidance. It must also preserve F-001's hybrid
  architecture when cross-layer or reuse guidance links to backend placement.

## 3. Perform Parent Integration Review

- After all child corrections are complete, inspect the combined specification
  diff for stale implementation names, contradictory ownership claims,
  duplicate canonical contracts, broken links, and generic/template wording.
- Run the final parent validation:

```powershell
python .trellis/scripts/spec_wiki.py lint
python .trellis/scripts/task.py validate .trellis/tasks/08-07-refresh-trellis-spec-architecture
git diff --check
git diff --cached --check
```

- Run child-specific validation commands before this integration gate. A full
  backend/frontend product gate is unnecessary unless source revalidation
  reveals a real product mismatch.

## Rollback Points

- Revert only the child-owned documentation change that fails semantic review
  or lint; never revert another child's accepted correction or unrelated
  worktree changes.
- Retain the audit evidence register and child PRDs even if an implementation
  requires replanning.

## Completion Gate

- Re-read the parent artifacts, evidence register, and every child PRD before
  declaring the tree ready for implementation.
- Do not call `task.py start` for this parent. Start only a reviewed child
  that has direct implementation work and its required planning artifacts.
- Archive the parent only after all child tasks are completed and the final
  integration gate passes.
