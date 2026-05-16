# Component Guidelines

> Component placement and reuse rules for this repository.

---

## Overview

The main frontend risk in this repo is false sharing: pushing page-specific or business-specific UI into `shared/*` too early. Use component placement as an architecture decision, not just an import convenience.

---

## Current Reality

- Page components live in domain pages:
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
  - [`frontend/src/platform/system/pages/AdminUsersPage.tsx`](../../../frontend/src/platform/system/pages/AdminUsersPage.tsx)
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Page-private components stay close to their domain:
  - [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx)
  - [`frontend/src/platform/system/components/users/UserActionsMenu.tsx`](../../../frontend/src/platform/system/components/users/UserActionsMenu.tsx)
- Truly reusable UI already exists under grouped shared folders:
  - [`frontend/src/shared/components/feedback/ErrorState.tsx`](../../../frontend/src/shared/components/feedback/ErrorState.tsx)
  - [`frontend/src/shared/components/table/index.ts`](../../../frontend/src/shared/components/table/index.ts)

---

## Placement Rules

- Put page implementations in `platform/*/pages` or `features/*/pages`.
- Put page-private components in the matching domain `components/*` folder.
- Move a component into `shared/*` only if all of these are true:
  - it is used by more than one page or domain
  - it does not depend on one domain's business vocabulary
  - it does not encode one page's workflow assumptions
- Prefer grouped shared barrels such as `@/shared/components/feedback`, `@/shared/components/layout`, or `@/shared/components/theme`.

---

## Shared Admission Test

Ask these before moving a component into `shared/*`:

1. Would this component still make sense outside the current feature or platform area?
2. Does it avoid domain-specific permission, API, or page-flow coupling?
3. Would another future page reuse it without needing to rename or partially rewrite it?

If the answer is no, keep it in the domain.

---

## Forbidden Regressions

- Do not recreate a flat `Common` dumping ground.
- Do not move page orchestration components into shared just to shorten imports.
- Do not edit generated UI primitives under `frontend/src/components/ui/**` directly when composition or wrapping is enough.

---

## Code Anchors

- Domain-local components: [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx), [`frontend/src/platform/system/components/users/UserActionsMenu.tsx`](../../../frontend/src/platform/system/components/users/UserActionsMenu.tsx)
- Shared grouped UI: [`frontend/src/shared/components/feedback/ErrorState.tsx`](../../../frontend/src/shared/components/feedback/ErrorState.tsx), [`frontend/src/shared/components/layout/Footer.tsx`](../../../frontend/src/shared/components/layout/Footer.tsx)
- Page composition examples: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
