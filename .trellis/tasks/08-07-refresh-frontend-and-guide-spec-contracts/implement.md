# Implementation Plan: Refresh Frontend And Guide Spec Contracts

## 1. Revalidate The Evidence

- Use CodeGraph to confirm `requirePermission`, `hasPermission`,
  route-local `validateSearch`, action capabilities, and the scheduler-to-
  inventory pagination import.
- Read the active frontend and thinking-guide contracts before editing.
- Confirm F-001 and F-002 remain correct in their active backend specs.

## 2. Correct Canonical Frontend Contracts

- In `frontend/route-permission-navigation-contract.md`, replace the retired
  `requireSuperuser` / `canAccessAdmin` signatures and examples with
  `requirePermission(permission: PermissionCode)`, permission-query data,
  `hasPermission`, and permission-filtered menu items.
- Allow `validateSearch` alongside route declaration, guards, metadata, and
  page imports; keep page implementation and feature orchestration out of
  `routes/*`.
- In `frontend/state-management.md`, point permission behavior to
  `app/permissions.ts` and its React/route entrypoints, not generic
  current-user derivation.
- In `frontend/component-guidelines.md`, forbid new feature-to-feature utility
  imports. Route domain-neutral shared behavior through the existing shared
  admission test; permit trivial local duplication. Record the current
  scheduler-to-inventory pagination dependency as a non-blocking cleanup.

## 3. Correct Thinking And Governance Guides

- In `guides/cross-layer-thinking-guide.md` and
  `guides/code-reuse-thinking-guide.md`, describe the supported simple
  `route -> service -> CRUD -> model/schema` path and the bounded operational
  module path. Link to canonical frontend contracts instead of repeating their
  signatures.
- Replace the retired `is_superuser` example and state CodeGraph-first source
  understanding, with `rg` reserved for narrow text, spec, and link checks.
- Align `guides/index.md` with that CodeGraph-first rule.
- In `spec/index.md`, remove the dated merge event from the active-current
  description. Do not split, move, or reformat the database or async guides.

## 4. Validate

Run from the repository root:

```powershell
rg -n 'requireSuperuser|canAccessAdmin|is_superuser|Prefer `rg` in this repo' .trellis/spec
rg -n "requirePermission|PermissionCode|validateSearch|feature-to-feature|CodeGraph" .trellis/spec/frontend .trellis/spec/guides
python .trellis/scripts/spec_wiki.py lint
python .trellis/scripts/task.py validate .trellis/tasks/08-07-refresh-frontend-and-guide-spec-contracts
git diff --check
git diff --cached --check
```

Review the complete diff to confirm that only active specs and this task's
artifacts changed, that F-001/F-002 remain intact, and that no product-source
cleanup was pulled into the documentation task.

## Rollback Point

Revert only the affected active-spec wording if it conflicts with current
source. Preserve the planning artifacts and source snapshot so the parent can
re-evaluate the remaining findings.

## Completion Gate

- The PRD, design, and implementation plan agree on the necessary F-003 to
  F-005 corrections and the narrow F-006 governance update.
- The broad backend-guide split is explicitly deferred with its trigger for
  reconsideration.
- Both context manifests contain real specification or research entries.
- The user reviews and explicitly approves this final planning summary before
  `task.py start`.
