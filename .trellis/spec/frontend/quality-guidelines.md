# Quality Guidelines

> Code quality standards for frontend development.

---

## Overview

Frontend work in this repo must preserve the existing React + Vite + TanStack structure, avoid churn in generated files, and keep changes focused on the intended user-facing behavior.

---

## Forbidden Patterns

- Do not edit generated files directly:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`
  - `frontend/src/components/ui/**`
- Do not mass-format unrelated frontend files.
- Do not introduce relative import sprawl when the app already supports `@/` aliases.
- Do not change `.env` or secrets as part of normal task work.

---

## Required Patterns

- Use `type` imports where appropriate.
- Respect Biome formatting and lint rules, including double quotes and semicolons-as-needed behavior.
- Keep frontend changes aligned with existing app folders under `frontend/src/**`.
- Use project-local React guidance first; pull in `vercel-react-best-practices` when the task benefits from it.

---

## Testing Requirements

- Use `bun run lint` as the default frontend quality gate.
- Use `bun run build` when the change affects routing, type flow, or bundle-time correctness.
- Use Playwright when the task changes critical user flows or explicitly requires UI verification.
- If backend schema changes affect generated client usage, regenerate the client before validation.

---

## Code Review Checklist

- Is the change limited to the intended frontend area?
- Were generated files left untouched unless regeneration was explicitly required?
- Are imports, types, and aliases consistent with repo conventions?
- Was the appropriate level of lint/build/test verification run?
- If backend schema changed, was client regeneration handled?
