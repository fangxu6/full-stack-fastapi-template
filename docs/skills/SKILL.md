# Team Skills Guide

Lightweight skill activation rules to reduce repeated mistakes.

## Available Skills

### 1) `python-patterns`
- When to activate: writing, reviewing, refactoring, or designing Python modules/packages.
- Focus: readability, explicit behavior, modern type hints, robust exception handling, context managers, and Pythonic idioms.
- Key constraints:
  - Prefer clear code over clever tricks.
  - Use specific exceptions and exception chaining.
  - Use modern typing (`list[str]`, `dict[str, Any]`, `T | None`) where possible.
  - Avoid common anti-patterns (mutable defaults, bare `except`, `type(x) == ...`).
- Example:
  - Good: `def first(items: list[T]) -> T | None: ...`
  - Bad: untyped helper functions with implicit behavior.

### 2) `vercel-react-best-practices`
- When to activate: writing, reviewing, or refactoring React/Next.js code, especially performance-sensitive work.
- Focus: eliminating waterfalls, reducing bundle size, server/client rendering efficiency, and avoiding unnecessary re-renders.
- Key constraints:
  - Parallelize independent async work (`Promise.all`).
  - Avoid barrel imports for heavy libraries when direct imports are available.
  - Prefer explicit data boundaries between server and client components.
  - Use stable React patterns for effects, dependencies, and state updates.
- Example:
  - Good: start independent async calls early, await together.
  - Bad: sequential awaits that create request waterfalls.

## Usage Notes
- Only use skills that are actually relevant to the current task.
- Python tasks default to `python-patterns`.
- In this repo, regular Vite SPA React tasks should prefer `react-best-practices` as the first React performance reference, and only use `vercel-react-best-practices` when Next.js or server/client boundary rules are actually relevant.
- Next.js-specific or server/client boundary-heavy React tasks should default to `vercel-react-best-practices`.
- If a task spans both stacks, apply both skills to their respective parts.
