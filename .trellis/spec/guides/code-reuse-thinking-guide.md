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

Good: keep business checks in `services/*`, persistence helpers in `crud/*`,
and route handlers thin. Existing anchors:

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

Bad: checking `is_superuser` inline in page components, route files, and menu
config separately.

Good: use the existing route/permission/navigation split:

- route enforcement in `frontend/src/app/router/guards.ts`
- permission truth in `frontend/src/shared/permissions/index.ts`
- menu visibility in `frontend/src/app/navigation/menu-config.ts`

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
- Backend business orchestration belongs in `backend/app/services/*` until a
  real module boundary justifies `backend/app/modules/<name>/`.
- Backend persistence helpers belong in `backend/app/crud/*`.
- Frontend app-frame behavior belongs in `frontend/src/app/*`.
- Frontend business feature code belongs in `frontend/src/features/*`.
- Frontend platform capability code belongs in `frontend/src/platform/*`.
- Frontend shared code belongs in `frontend/src/shared/*` only after it passes
  the shared admission test in
  [`frontend/component-guidelines.md`](../frontend/component-guidelines.md).

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

## Checklist Before Commit

- [ ] Searched for existing similar code
- [ ] No copy-pasted logic that should be shared
- [ ] Permission and route logic still have one source of truth
- [ ] API contracts come from generated client types, not local rewrites
- [ ] Similar patterns follow the same structure
