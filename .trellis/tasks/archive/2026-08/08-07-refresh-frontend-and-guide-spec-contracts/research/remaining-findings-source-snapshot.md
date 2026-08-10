# Remaining Frontend And Guide Findings Snapshot

Captured during planning on 2026-08-10. Product source is read-only evidence
for this documentation-only task.

## F-003: Permission And Thin Routes

- `frontend/src/app/router/guards.ts:24-66` exports
  `requirePermission(permission)` and loads current permissions through
  `app/permissions.ts`.
- `frontend/src/shared/permissions/index.ts:1-23` defines `PermissionCode`
  and pure `hasPermission`.
- `frontend/src/app/navigation/menu-config.ts:73-78` filters navigation with
  that same permission helper.
- `frontend/src/routes/_layout/inventory/corrections.tsx:7-15` stays thin
  while declaring both `beforeLoad: requirePermission(...)` and Zod
  `validateSearch`.
- `frontend/src/features/inventory/correction-workspace.ts:37-54` derives
  request, review, and recovery capabilities separately from page access.

The route-permission contract still names `requireSuperuser` and
`canAccessAdmin`, and state guidance still says permissions are derived from
current-user data. Both active claims are stale.

## F-004 And F-005: Guide And Feature Boundaries

- The cross-layer and reuse guides still use service/CRUD as their only
  concrete backend path, and the reuse guide uses `is_superuser` as a bad
  example.
- `guides/index.md:129-137` still prefers `rg` for source exploration, which
  conflicts with this indexed repository's CodeGraph-first instruction.
- `frontend/src/features/scheduler/pages/SchedulerJobsPage.tsx:43-47` imports
  generic pagination values from `features/inventory/pagination.ts`.
- `frontend/component-guidelines.md` has a shared admission test but no
  explicit rule that stops a new feature from using another feature as a
  utility provider.

## F-006: Necessary Governance, Deferred Reorganization

`.trellis/spec/index.md:13-20` names the 2026-07-08 merge as the current
repository baseline. That active-current phrasing is stale. The database and
async guides are long, but `backend/index.md` already provides trigger routing
and their scenario contracts are the current durable owners. No source or
spec evidence shows a broken navigation path or contradiction that would
justify a mechanical document split now.

## Verdict

Implement the active contract corrections and canonical-link cleanup. Defer
backend guide splitting until a concrete validation, navigation, or duplicate
contract failure demonstrates that it is needed.
