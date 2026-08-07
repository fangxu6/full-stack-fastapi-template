# Design: Correct Backend Hybrid Architecture Spec

## Boundary

This task corrects active documentation only. Current source is evidence; no
router, service, CRUD, module, test, schema, or runtime behavior changes.

## Canonical Contract

`backend/directory-structure.md` owns the placement decision because the
backend index already routes readers there before they choose a file location.
The other two documents keep only the amount of architecture context needed
for their role:

| Document | Responsibility after correction |
| --- | --- |
| `backend/directory-structure.md` | Define the two supported paths and the domain-complexity selection rule. |
| `backend/index.md` | State current hybrid reality, direct placement decisions to the directory guide, and keep trigger routing current. |
| `backend/quality-guidelines.md` | Check that a change follows the chosen path without asserting a module-maturity migration. |

## Placement Contract

```text
simple CRUD:        api/routes -> services -> crud -> models/schemas
operational domain: modules/<domain>/router -> domain collaborators -> models/schemas
cross-cutting:      core/* or infra/* when the responsibility is reusable platform behavior
```

The module path is justified by actual bounded-domain complexity, including
multi-table state transitions, durable asynchronous work, external integration,
events, or collaboration across domains. It is not selected merely because a
feature is new or because the project has a `modules/` directory.

## Source Anchors

- `backend/app/api/routes/items.py` is the lightweight reference path.
- `backend/app/api/main.py` proves the production API currently aggregates
  module routers alongside conventional routes.
- Inventory correction, IAM, and scheduler routers are operational module-path
  examples. The detailed evidence is in
  [research/backend-hybrid-architecture-evidence.md](research/backend-hybrid-architecture-evidence.md).

## Compatibility And Rollback

The change alters no runtime behavior. The documentation risks are overstating
the API status of every module or recreating the same contract in three files.
Review source anchors and cross-links before finalizing. If a statement cannot
be anchored, remove it; if a document becomes contradictory, revert only that
document and retain the canonical directory contract.
