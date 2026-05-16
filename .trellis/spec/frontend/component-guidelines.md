# Component Guidelines

> How components are built in this project.

---

## Overview

Frontend components are React function components written in TypeScript. The codebase mixes app-shell components under `src/app/**`, feature components under `src/features/**` and `src/platform/**`, and reusable primitives under `src/components/**` and `src/shared/**`.

---

## Component Structure

- Page-level components usually compose data fetching + layout wrappers, for example [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx) and [`frontend/src/platform/system/pages/AdminUsersPage.tsx`](../../../frontend/src/platform/system/pages/AdminUsersPage.tsx).
- Dialog and action components typically keep local UI state near the component, for example [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx).
- App-shell components such as [`frontend/src/app/layout/AppLayout.tsx`](../../../frontend/src/app/layout/AppLayout.tsx) focus on composition and routing outlets rather than business logic.
- Prefer simple exported functions like `export function ItemsPage()` or default function components when the file only owns one component.

---

## Props Conventions

- Use TypeScript types for props when a component needs explicit input contracts.
- Keep feature-specific table row shapes or action contracts local to the feature when they are not broadly shared, as seen in `UserTableData` usage in [`frontend/src/platform/system/pages/AdminUsersPage.tsx`](../../../frontend/src/platform/system/pages/AdminUsersPage.tsx).
- Prefer imported API client types when a component works directly with backend entities, for example `type UserPublic` or `type ItemCreate`.

---

## Styling Patterns

- Tailwind utility classes are the primary styling mechanism.
- Reusable UI primitives come from `src/components/ui/**`, usually wrapping shadcn/Radix-based components.
- Keep layout classes inline in JSX unless a helper or shared primitive already exists.
- Use shared feedback/table primitives from `src/shared/components/**` instead of rebuilding common empty/loading/table states.

---

## Accessibility

- Prefer existing Radix/shadcn primitives for dialogs, menus, form controls, and layout chrome because they already carry accessibility behavior.
- Keep form labels, messages, and button states wired through shared form primitives, as shown in [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx).
- Preserve semantic headings and descriptive text on page shells.

---

## Common Mistakes

- Editing generated UI files under `src/components/ui/**` directly instead of wrapping or composing them.
- Pushing too much server-state logic into layout or shell components instead of keeping it in feature pages or hooks.
- Replacing shared feedback or table primitives with one-off copies that drift in behavior or styling.
