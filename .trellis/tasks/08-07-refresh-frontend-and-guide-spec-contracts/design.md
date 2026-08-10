# Design: Refresh Frontend And Guide Spec Contracts

## Objective

Correct active documentation that names retired frontend permission interfaces,
omits valid thin-route responsibilities, and leaves a cross-feature dependency
gap. Preserve the completed backend hybrid and scheduler-lifecycle contracts.
This is documentation-only work; source is read-only evidence.

## Necessary Scope

| Finding | Decision | Canonical owner |
| --- | --- | --- |
| F-003 | Correct obsolete superuser wording and document permission-query access, thin-route search validation, and action capabilities. | `frontend/route-permission-navigation-contract.md`, with query ownership in `frontend/state-management.md`. |
| F-004 | Make thinking guides describe both simple CRUD and bounded operational modules; use CodeGraph before source exploration and replace retired examples. | `guides/cross-layer-thinking-guide.md`, `guides/code-reuse-thinking-guide.md`, `guides/index.md`. |
| F-005 | Prohibit new imports from one `features/*` domain to another. Admit domain-neutral shared code through the existing test or keep trivial code local. | `frontend/component-guidelines.md`. |
| F-006 | Remove the dated active-current catalog claim and reduce duplicate frontend signatures through canonical links. Do not split long backend guides solely for size. | `spec/index.md` plus the canonical documents above. |

## Contract Model

1. `app/permissions.ts` fetches current permission data for React and route
   guards; `shared/permissions` stays pure (`PermissionCode` and
   `hasPermission`).
2. `app/router/guards.ts::requirePermission(permission)` gates page access;
   `app/navigation/menu-config.ts` derives visibility from the same code.
   A route may declare transport metadata such as `validateSearch`, but page
   implementation remains under `platform/*/pages` or `features/*/pages`.
3. A page can show or hide request/review/recovery controls using a narrower
   action capability, but the backend endpoint is still authorization
   authority.
4. A feature may not use another feature as its utility module. Existing
   `SchedulerJobsPage -> inventory/pagination` remains a recorded source
   cleanup, not an in-scope code move.

## Compatibility And Boundaries

- Do not change `backend/app/**`, `frontend/src/**`, generated artifacts,
  tests, runtime configuration, API contracts, or migrations.
- Keep the current F-001 hybrid backend rule and F-002
  `execution.execute(...) -> SchedulerRunOutcome -> finish_outcome(...)`
  lifecycle rule unchanged.
- Existing database and async scenario documents remain their own durable
  owners. A future split requires evidence of a broken link, repeated
  contradiction, or unusable trigger routing; line count is insufficient.

## Validation Design

- Re-check source-backed names with CodeGraph before edits.
- Search active specs for `requireSuperuser`, `canAccessAdmin`, `is_superuser`,
  and the `Prefer rg` rule.
- Review the final guide wording against the five canonical owners above.
- Run spec lint, task-manifest validation, and whitespace checks. Runtime,
  frontend, and API E2E checks are not required because no behavior changes.
