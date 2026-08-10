# Code Reuse Thinking Guide

> Purpose: search for existing backend/frontend patterns before adding new
> helpers, components, hooks, services, or shared abstractions.

---

## The Problem

Duplicated code is a common source of inconsistency bugs.

When you copy-paste or rewrite existing logic:

- bug fixes do not propagate
- behavior diverges over time
- route, permission, and API contracts become harder to reason about
- future agents have to infer which duplicate is authoritative

---

## Before Writing New Code

### Step 1: Search First

Use CodeGraph first when you need to understand a code path or symbol impact in
this indexed repository. Use `rg` for lightweight text checks, generated-file
boundaries, and spec/document searches.

```bash
codegraph explore "functionName domainKeyword"
codegraph node path/to/file
rg "functionName|domainKeyword" backend/app frontend/src .trellis/spec
rg --files backend/app frontend/src | rg "service|crud|Page|Dialog|Table|guard|permission"
```

### Step 2: Ask These Questions

| Question | If yes |
| --- | --- |
| Does a similar function exist? | Use or extend it. |
| Is this pattern used elsewhere? | Follow the existing pattern. |
| Could this be a shared utility? | Put it in the right layer, not the nearest folder. |
| Am I copying code from another file? | Stop and decide whether extraction is justified. |

---

## Common Duplication Patterns

### Pattern 1: Backend Service And CRUD Duplication

Bad: duplicating permission or ownership checks in multiple route handlers.

Good: keep simple CRUD on `api/routes -> services -> crud -> models/schemas`;
keep route handlers thin, business checks in `services/*`, and persistence
helpers in `crud/*`. Use a bounded `modules/*` workflow only where real
orchestration, lifecycle, or ownership complexity earns that boundary. Existing
simple CRUD anchors:

- `backend/app/api/routes/items.py`
- `backend/app/services/item.py`
- `backend/app/crud/item.py`

### Pattern 2: Similar Frontend Components

Bad: creating a new domain-specific copy of an existing dialog, table, empty
state, or loading button because imports were inconvenient.

Good: reuse or compose existing UI primitives and shared grouped components when
they are truly cross-domain. Keep domain-specific workflow components in their
domain folder. Existing anchors:

- `frontend/src/features/items/components/AddItemDialog.tsx`
- `frontend/src/platform/system/components/users/UserActionsMenu.tsx`
- `frontend/src/shared/components/table/index.ts`
- `frontend/src/shared/components/feedback/ErrorState.tsx`

### Pattern 3: Permission And Route Logic Duplication

Bad: inventing page-local permission flags in page components, route files, and
menu config separately.

Good: use the canonical
[`frontend/route-permission-navigation-contract.md`](../frontend/route-permission-navigation-contract.md)
for the route/permission/navigation split instead of repeating permission
entrypoints here.

### Pattern 4: API Contract Duplication

Bad: rewriting generated request/response types locally for convenience.

Good: use generated types and services from `frontend/src/client/**`; regenerate
them with `bash ./scripts/generate-client.sh` after backend contract changes.

---

## When To Abstract

Abstract when:

- the same code appears 3 or more times
- logic is complex enough to have bugs
- multiple pages, services, or modules already need the same behavior
- the abstraction preserves the current layer boundaries

Do not abstract when:

- only one caller exists
- the code is a trivial one-liner
- the abstraction would be more complex than duplication
- the code is page-specific and would make `shared/*` carry one domain's
  workflow assumptions

---

## Placement Guide

- Backend cross-cutting platform behavior belongs in `backend/app/core/*`.
- Simple backend business orchestration belongs in `backend/app/services/*`;
  use `backend/app/modules/<name>/` only for a bounded operational domain with
  complexity that justifies the boundary.
- Backend persistence helpers belong in `backend/app/crud/*`.
- Frontend app-frame behavior belongs in `frontend/src/app/*`.
- Frontend business feature code belongs in `frontend/src/features/*`.
- Frontend platform capability code belongs in `frontend/src/platform/*`.
- Frontend shared code belongs in `frontend/src/shared/*` only after it passes
  the shared admission test in
  [`frontend/component-guidelines.md`](../frontend/component-guidelines.md).
- A feature must not use another `features/*` domain as its utility module;
  keep trivial duplication local or admit genuinely domain-neutral code to
  `shared/*` through that same contract.

---

## Gotcha: False Sharing

The main frontend reuse risk in this repo is moving code to `shared/*` before it
is actually shared. A component used by one page should usually stay near that
page, even if it might be reused someday. Promote it only when another domain
actually needs it or when the abstraction removes real duplicated behavior.

The main backend reuse risk is putting business rules into low-level helpers or
`crud/*` because more than one route needs them. Shared business behavior should
live in services or a deliberate module boundary, not in persistence helpers.

---

## Gotcha: Batch-Change Backcheck

When you change a repeated pattern in more than one file, do a second search
after the first edit. Batch edits often miss the one variant that uses a
different name or import path.

Examples:

- If a service error contract changes, search for the same `detail` text,
  exception class, and status code in routes, services, tests, and frontend
  consumers.
- If a frontend table/action/menu pattern changes, search for both component
  names and route/menu labels.
- If a generated-client consumer changes, search for both the service name and
  the generated type name.

---

## Gotcha: Asymmetric Mechanism Drift

This repo has several pairs where one side is generated or centralized and the
other side is hand-authored. A directory or contract change can easily update
one mechanism but not the other.

High-risk pairs:

- backend OpenAPI schemas -> generated `frontend/src/client/**`
- TanStack route files -> generated `frontend/src/routeTree.gen.ts`
- route guards -> menu visibility -> shared permission helpers
- `.trellis/spec/**` files -> `.trellis/spec/index.md` catalog
- docs indexes such as `docs/README.md` -> newly added docs

When touching one side, explicitly check whether the paired side should be
regenerated, edited, or documented as intentionally unchanged.

---

## Checklist Before Commit

- [ ] Searched for existing similar code
- [ ] No copy-pasted logic that should be shared
- [ ] Permission and route logic still have one source of truth
- [ ] API contracts come from generated client types, not local rewrites
- [ ] Similar patterns follow the same structure
- [ ] Batch-change backcheck ran for repeated patterns
- [ ] Generated/centralized companion files were reviewed
