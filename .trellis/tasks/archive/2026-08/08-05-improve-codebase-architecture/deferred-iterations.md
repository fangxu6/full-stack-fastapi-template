# Permission Access Deferred Iterations

## Purpose

Keep route/menu permission metadata consolidation visible without expanding the
current caller-migration scope.

## Traceability Rules

- Deferred items do not fail the current task acceptance criteria.
- Each item needs an independent task before implementation.
- Do not derive metadata by parsing or editing generated
  `frontend/src/routeTree.gen.ts`.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
|---|---|---|---|---|
| D-001 | Make route/menu permission metadata come from one typed route-access source | It is a separate navigation metadata design problem; the current task only repairs permission data access locality | Current permission access module repair | Independent PRD, design, implementation plan, route/menu drift tests, generated-route review |

## Remaining Work In Current Scope

- D-001 is not part of the current acceptance criteria.
- The current task only migrates `InventoryCorrectionsPage` and adds the
  focused permission-guard E2E assertion.
