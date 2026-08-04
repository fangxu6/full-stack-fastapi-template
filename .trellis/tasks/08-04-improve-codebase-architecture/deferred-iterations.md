# Permission architecture deferred iterations

## Purpose

Keep the approved route/menu permission metadata consolidation visible without
expanding the current Stage 1 delivery boundary.

## Traceability Rules

- Deferred items do not fail the current Stage 1 acceptance criteria.
- Each item needs an independent task before implementation.
- Dependencies must be satisfied before a dependent item is started.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
|---|---|---|---|---|
| D-001 | Make route/menu permission metadata come from one typed route-access source | It is valuable long term but is a separate metadata and route-generation design problem; Stage 1 can remove duplicated permission fetching without coupling navigation to generated route output | Stage 1 permission access module; inventory of protected routes and menu items | Independent PRD, design, implementation plan, route/menu drift tests, and generated-route review |

## Suggested Iteration Order

D-001 follows Stage 1 so the future metadata source can consume the stable
permission access module without mixing fetch locality and navigation metadata
ownership in one change.

## Carry-Forward Acceptance Notes

- Route guards remain the authorization enforcement point.
- Menu filtering remains presentation only.
- Do not parse or hand-edit `frontend/src/routeTree.gen.ts`.
- The future source must cover every protected route and every permissioned
  menu item, including entries without a visible menu item.

## Remaining Work In Current Scope

- Stage 1 is implemented and validated. No additional Stage 1 work remains.
- D-001 requires an independent follow-up task when route/menu permission
  metadata consolidation is scheduled.
