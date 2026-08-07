# Backend Hybrid Architecture Evidence

## Purpose

Record the current source and specification evidence for F-001 so the task can
be implemented without relying on template-era assumptions.

## Active Specification Drift

| File | Stale claim | Required correction |
| --- | --- | --- |
| `.trellis/spec/backend/index.md:9-15,61-79` | Calls the repository a `platform-batch-0 transition`; calls `modules/*` future-facing. | Describe the current hybrid architecture and link placement decisions to the directory guide. |
| `.trellis/spec/backend/directory-structure.md:9,45-47,69-70` | Calls modules future-facing/secondary until richer. | Make this the canonical placement contract with two supported paths. |
| `.trellis/spec/backend/quality-guidelines.md:249-261` | Says `modules/*` is not already mature. | Replace the migration narrative with review checks compatible with both paths. |

## Current Source Evidence

- CodeGraph read of `backend/app/api/main.py:18-23` shows API aggregation of
  `items.router`, inventory, inventory-correction, IAM, scheduler, and generic
  modules routers. The inventory, IAM, and scheduler entries are active
  production routes, not a future-only scaffold.
- CodeGraph read of `backend/app/api/routes/items.py:14-72` shows a thin,
  lightweight CRUD route delegating every operation to `services.item`.
- CodeGraph reads of `backend/app/modules/inventory/correction_router.py`,
  `backend/app/modules/iam/router.py`, and
  `backend/app/modules/scheduler/router.py` show module routers delegating to
  their domain-local collaborators. Inventory correction has workflow and
  scheduled-work concerns; IAM owns role/permission work; scheduler owns job
  management.
- `backend/app/modules/` also contains audit, auth, file, items, and system
  boundaries. Router registration should not be used to overstate which of
  those are public API domains; each claim must remain anchored to source.

## Planning Decision

`directory-structure.md` is already the first required read for file placement
in `backend/index.md`. It is therefore the canonical owner. Updating it and
making the index and quality guide refer to the same contract is smaller and
less drift-prone than adding another architecture guide.

## Evidence Limits

- This is documentation planning. It authorizes no product-source change.
- The F-002 child owns scheduler lifecycle wording; do not reproduce or alter
  that contract here.
