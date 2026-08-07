# Implementation Plan: Correct Backend Hybrid Architecture Spec

## 1. Revalidate Evidence

- Use CodeGraph to re-read `backend/app/api/main.py`,
  `backend/app/api/routes/items.py`, and the inventory, IAM, and scheduler
  router boundaries immediately before editing.
- Re-read the three target specification documents and update the research
  record if source ownership changed.

## 2. Establish The Canonical Placement Rule

- Update `backend/directory-structure.md` first. Replace the transition and
  future-module wording with the two supported placement paths and the
  complexity-based selection rule.
- Keep `api/routes/items.py -> services/item.py -> crud/item.py` as the
  concrete simple-CRUD example. Do not prescribe module migration.
- Describe only the operational module examples that current source supports;
  do not infer public-router status for every module directory.

## 3. Align Supporting Backend Guidance

- Update `backend/index.md` to describe the current hybrid architecture and
  direct placement decisions to `directory-structure.md`.
- Update `backend/quality-guidelines.md` so review guidance verifies the
  selected path rather than describing an unfinished migration.
- Update only required indexes and links. Do not create a new architecture
  guide or repeat low-level path signatures in supporting documents.

## 4. Record And Validate

- Run `python .trellis/scripts/spec_wiki.py index` only if the document tree
  changes; otherwise do not regenerate an unchanged catalog.
- Append the required concise specification maintenance-log entry, then run:

```powershell
python .trellis/scripts/spec_wiki.py log --type update --title "Correct backend hybrid architecture guidance" --details "Replaced template-era future-module wording with the source-backed hybrid placement contract."
python .trellis/scripts/spec_wiki.py lint
$staleArchitectureTerms = rg -n -i "platform-batch-0 transition|future-facing|transitional architecture state|secondary until|until modules/\* becomes richer|mature" .trellis/spec/backend/index.md .trellis/spec/backend/directory-structure.md .trellis/spec/backend/quality-guidelines.md
if ($LASTEXITCODE -eq 0) { $staleArchitectureTerms; throw "Stale backend architecture text remains." }
if ($LASTEXITCODE -ne 1) { throw "Stale-term search failed." }
python .trellis/scripts/task.py validate .trellis/tasks/08-07-correct-backend-hybrid-architecture-spec
git diff --check
git diff --cached --check
```

- Inspect the final specification diff for contradictory placement rules and
  for unintended changes outside the task scope. No API E2E test is required:
  this task changes documentation only.

## Rollback Points

- Keep the existing placement sections until their replacement is linked and
  source-anchored.
- Revert only the affected documentation edit if lint or semantic review fails;
  never revert product source or another child task's work.

## Activation Gate

- The PRD, design, implementation plan, research evidence, and curated
  sub-agent context must be reviewed before `task.py start`.
- This task remains in `planning` until the user explicitly approves the final
  planning summary.
