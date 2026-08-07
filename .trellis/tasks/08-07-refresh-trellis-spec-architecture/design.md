# Design: Coordinate Trellis Spec Architecture Refresh

## Boundary

The parent changes only task planning artifacts. It coordinates the
source-backed documentation work without becoming an implementation target.
Product code remains read-only evidence, and each child task owns the active
specification files for its finding set.

## Child Contract Owners

| Contract set | Owning child | Parent integration responsibility |
| --- | --- | --- |
| Hybrid backend placement | `08-07-correct-backend-hybrid-architecture-spec` | Confirm simple CRUD and operational modules remain compatible statements. |
| Scheduler lifecycle | `08-07-correct-scheduler-lifecycle-spec` | Confirm the current ownership contract is preserved by any later async-guide reorganization. |
| Frontend access, reusable boundaries, guide governance | `08-07-refresh-frontend-and-guide-spec-contracts` | Confirm canonical links do not contradict the two P1 contracts. |

## Integration Model

1. Each child independently revalidates its named source evidence and records
   only the active-specification correction within its scope.
2. The remaining-findings child incorporates the completed scheduler ownership
   wording before moving or trigger-routing any async scenario.
3. Parent integration reviews the combined active spec diff for contradictory
   terms, duplicate implementation signatures, broken links, and missing
   maintenance-log/catalog updates.

The two P1 children may be planned and implemented independently. The third
child may plan in parallel but must use their final active contracts when it
touches shared indexes or reorganizes async guidance. This ordering prevents a
large documentation move from restoring the removed scheduler API.

## Compatibility And Rollback

No runtime compatibility risk exists. The integration risk is a broken link or
a child correction being contradicted by another child. Revert only the
affected child-owned documentation move; preserve the parent evidence and task
map for repeatable review.
