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
- UI primitives live under `frontend/src/components/ui/**` and are treated as vendor-style generated primitives for normal feature work.
- Ant Design is available as a gradual complex-component layer, not a
  replacement for the existing shadcn/ui primitive layer:
  - [`frontend/src/app/providers/AntdProvider.tsx`](../../../frontend/src/app/providers/AntdProvider.tsx)
  - [`frontend/src/platform/docs/pages/RulesPage.tsx`](../../../frontend/src/platform/docs/pages/RulesPage.tsx)

---

## Placement Rules

- Put page implementations in `platform/*/pages` or `features/*/pages`.
- Put page-private components in the matching domain `components/*` folder.
- Move a component into `shared/*` only if all of these are true:
  - it is used by more than one page or domain
  - it does not depend on one domain's business vocabulary
  - it does not encode one page's workflow assumptions
- Prefer grouped shared barrels such as `@/shared/components/feedback`, `@/shared/components/layout`, or `@/shared/components/theme`.

## Ant Design Boundary

- **Default for new business-management surfaces:** use the installed Ant
  Design 6 package (`antd@^6.5.0`) for new data-dense workflows under
  `features/*` or `platform/*`. This includes tables, filter/search forms,
  create/edit forms, date and selection controls, confirmation dialogs, and
  loading, empty, or error feedback. Do not rebuild local equivalents from
  low-level primitives unless the page has a concrete interaction need that
  Ant Design does not cover.
- Use Ant Design for complex enterprise UI surfaces where it removes real
  local composition: document browsers, dense lists, result/empty/error states,
  complex forms, date controls, upload flows, and future data-heavy tables.
- Keep existing shadcn/ui primitives for current app shell, auth, simple
  feature dialogs, and already-working page flows unless a task explicitly
  scopes a migration.
- Do not create a full wrapper layer around every Ant Design component. Import
  `antd` components directly in `app/*`, `platform/*`, or `features/*`; extract
  a local wrapper only when multiple pages need the same domain-neutral
  composition.
- Keep Ant Design provider and token wiring in `app/providers/*`; page code
  should not configure global Ant Design theme.
- Import Ant Design components directly from `antd` inside the owning feature
  or platform module. The global provider is already mounted through
  [`frontend/src/app/providers/AntdProvider.tsx`](../../../frontend/src/app/providers/AntdProvider.tsx).
- `shared/excel` is the explicit shared exception: `ExcelImportDialog` remains
  generic and may import Ant Design directly. The component-policy hook allows
  this sub-root only; other `shared/*` code must remain free of Ant Design.
- Do not adopt `@ant-design/pro-components` until its peer dependencies and
  project need are reviewed in a dedicated task.

## Remote Business Selects

- For business Select fields whose option set can outgrow a small bounded list,
  use the existing server-side list endpoint with a domain-local remote-search
  hook. Do not load a fixed first page and apply client-side filtering.
- Use Ant Design Select's remote-search contract: `showSearch`,
  `filterOption={false}`, debounced query input, and explicit loading, empty,
  and failure feedback.
- Keep scope predicates aligned with the workflow: historical filters may need
  inactive records, while create and edit forms must request only choices that
  the server permits for writes.
- Keep the remote option behavior in the owning feature when its API vocabulary
  or eligibility rules are domain-specific; do not promote it to `shared/*`
  prematurely.

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
- Do not make a page-private component shared because it may be reused someday;
  wait until another page or domain actually needs it.
- Do not interpret Ant Design adoption as permission to replace existing
  shadcn/ui pages wholesale.

---

## Code Anchors

- Domain-local components: [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx), [`frontend/src/platform/system/components/users/UserActionsMenu.tsx`](../../../frontend/src/platform/system/components/users/UserActionsMenu.tsx)
- Shared grouped UI: [`frontend/src/shared/components/feedback/ErrorState.tsx`](../../../frontend/src/shared/components/feedback/ErrorState.tsx), [`frontend/src/shared/components/layout/Footer.tsx`](../../../frontend/src/shared/components/layout/Footer.tsx)
- Page composition examples: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)
- Vendor-style UI primitives: [`frontend/src/components/ui/button.tsx`](../../../frontend/src/components/ui/button.tsx)
- Ant Design provider and pilot: [`frontend/src/app/providers/AntdProvider.tsx`](../../../frontend/src/app/providers/AntdProvider.tsx), [`frontend/src/platform/docs/pages/RulesPage.tsx`](../../../frontend/src/platform/docs/pages/RulesPage.tsx)
