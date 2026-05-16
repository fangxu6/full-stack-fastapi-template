# Type Safety

> Type safety patterns in this project.

---

## Overview

The frontend uses strict TypeScript, generated API client types from `frontend/src/client/**`, Zod for form validation, and feature-local helper types when a screen needs derived UI shape.

---

## Type Organization

- Backend contract types should come from the generated client whenever possible, for example `UserPublic`, `UserRegister`, and `ItemCreate`.
- Feature-local derived types belong near the feature that owns them, for example `UserTableData` inside the system/users UI area.
- Shared lightweight app types can live under `src/app/**`, `src/shared/**`, or local feature files depending on reuse scope.

---

## Validation

- Forms use Zod schemas with `zodResolver`, as shown in [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx).
- Let `z.infer<typeof schema>` derive form data types instead of duplicating form interfaces manually.
- Runtime API error shaping is handled through shared helpers such as [`frontend/src/utils.ts`](../../../frontend/src/utils.ts).

---

## Common Patterns

- Prefer `type` imports for type-only usage.
- Use inferred types from schemas and router/client factories where practical.
- Narrow permission checks through tiny helper functions such as [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts).
- Use generated client request/response types directly in hooks and mutations rather than recreating payload shapes by hand.

---

## Forbidden Patterns

- Avoid `any` unless there is no better boundary type and the escape hatch is tightly contained.
- Do not rewrite generated API client types locally just for convenience.
- Avoid broad type assertions when inference or schema-derived types already express the contract.
