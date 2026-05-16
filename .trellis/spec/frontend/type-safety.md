# Type Safety

> Type and validation rules for this repository's frontend.

---

## Overview

The frontend's type safety depends on three main contracts:

- generated OpenAPI client types
- Zod-backed form validation
- consistent alias/import discipline

---

## Current Reality

- Generated API contracts are consumed directly from `frontend/src/client/**`:
  - [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts)
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
- Forms use Zod schemas and inferred types:
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
  - [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx)
- Permission checks use narrow helper types instead of broad ad hoc assertions:
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)

---

## Required Patterns

- Prefer generated client request/response types over locally redefined API contracts.
- When using Zod, derive form types from the schema rather than duplicating interfaces.
- Prefer `type` imports for type-only usage.
- Prefer `@/` aliases in app code instead of deep relative import sprawl.

---

## Cross-Layer Rule

- If backend OpenAPI contracts change, regenerate the frontend client with `bash ./scripts/generate-client.sh` before treating the frontend work as complete.
- Do not manually patch generated client types as a substitute for regeneration.

---

## Recommended Direction

- Keep using the generated client as the single source of truth for API contracts.
- Use Zod validation at form boundaries and keep runtime error handling routed through shared helpers rather than broad `any` escapes.

---

## Forbidden Patterns

- Rewriting generated API payload types locally for convenience
- Broad `any` use where client types or schema inference already exist
- Skipping regeneration after backend contract changes and then patching compile errors by hand

---

## Code Anchors

- Generated-client usage: [`frontend/src/hooks/useAuth.ts`](../../../frontend/src/hooks/useAuth.ts), [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
- Zod inference: [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx), [`frontend/src/features/items/components/AddItemDialog.tsx`](../../../frontend/src/features/items/components/AddItemDialog.tsx)
- Narrow permission typing: [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
