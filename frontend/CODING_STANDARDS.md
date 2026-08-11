# Frontend Coding Standards

This document defines the frontend coding standards for `frontend/` in this repository.

## 1. Scope and Principles

- Scope: all TypeScript/React code in `frontend/src`, tests in `frontend/tests`, and frontend build/test config.
- Favor clear, composable components and predictable data flow.
- Keep diffs focused; avoid broad style-only churn unrelated to the task.

## 2. Language and Toolchain Baseline

- Language: TypeScript with React.
- Runtime/tooling: Bun for package scripts and local dev workflows.
- Build: `vite` with TypeScript compile step.
- Lint/format: Biome (`biome check --write --unsafe ...`) using repo configuration.
- E2E testing: Playwright.

## 3. Project Structure

- Routes live in `frontend/src/routes/` (TanStack Router).
- App shell, navigation, and router guards live in `frontend/src/app/`.
- Cross-business capabilities such as auth live in `frontend/src/platform/`.
- Business feature code lives in `frontend/src/features/`.
- Reusable UI, generic hooks, and utilities live in `frontend/src/shared/`.
- Generated OpenAPI client lives in `frontend/src/client/`.

## 4. Naming Conventions

- React components and component files: `PascalCase` (e.g. `AuthLayout.tsx`).
- Hooks: `camelCase` with `use` prefix (e.g. `useAuth.ts`).
- Utility files/functions: `camelCase` function names, concise descriptive file names.
- Constants: `UPPER_SNAKE_CASE` when values are immutable and global.

## 5. Imports and Module Boundaries

- Prefer `@/` alias for app imports.
- Prefer type-only imports where applicable: `import { type Foo } from "...";`.
- Keep feature logic out of generated client files; wrap API calls in app-level hooks/services when needed.

## 6. Formatting and Style Rules

- Follow Biome formatting defaults for this project.
- Use double quotes for JavaScript/TypeScript strings.
- Use semicolons as configured by Biome (`asNeeded` in current config).
- Keep JSX readable; split large components into smaller presentational units.

## 7. React and State Management

- Keep components focused and as pure as practical.
- Keep side effects in hooks (`useEffect`/custom hooks), not during render.
- Use TanStack Query patterns for server-state fetching/caching.
- Keep route-level data concerns in route or hook layers, not deep UI leaf components.

## 8. Styling and UI Patterns

- Use the existing Tailwind + shadcn/ui design system consistently.
- Do not manually edit generated shadcn base files under `src/shared/components/ui/**` unless intentionally customizing and reviewed.
- Prefer composition over one-off duplicated utility class blocks.

## 9. Error Handling and UX

- Surface actionable user-facing errors for API failures.
- Keep loading, empty, and error states explicit for async views.
- Use existing shared components/patterns for fallback UI and notifications.

## 10. Testing and Verification

- Add or update Playwright tests for user-visible flow changes.
- Keep tests deterministic and avoid brittle selectors.
- For logic-heavy utilities/hooks, consider adding focused unit tests when test setup exists.

Run these before submitting frontend changes:

```bash
cd frontend
bun install
bun run lint
bun run build
bunx playwright test
```

## 11. Generated and Restricted Areas

- Do not edit generated files directly:
  - `frontend/src/client/**`
  - `frontend/src/routeTree.gen.ts`
  - `frontend/src/shared/components/ui/**`
- If backend OpenAPI changes, regenerate client with `bash ./scripts/generate-client.sh` from repo root.

## 12. Pull Request Expectations

- Keep each PR scoped to a coherent frontend change.
- Document user-visible behavior changes and any route/API coupling.
- Include screenshots or short recordings for non-trivial UI updates when useful.
