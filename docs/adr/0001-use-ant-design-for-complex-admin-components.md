# Use Ant Design for Complex Admin Components

This frontend already has a working Tailwind + shadcn/ui primitive layer, so Ant Design is adopted as a gradual complex-component layer rather than a replacement design system. New data-dense admin experiences may use `antd` components under the existing React/Vite/TanStack structure, while existing shadcn/ui pages should not be migrated unless a later task proves a concrete payoff.

## Considered Options

- Keep shadcn/ui only: lowest dependency cost, but leaves complex enterprise UI patterns to local composition.
- Adopt Ant Design for complex admin components: gives richer tables, lists, feedback, empty states, and form/page patterns without forcing a full migration.
- Replace shadcn/ui with Ant Design: higher visual consistency long term, but too much regression risk for the current app.

## Consequences

- The app may temporarily use both shadcn/ui primitives and Ant Design components.
- Ant Design usage must be documented in the frontend spec and verified through a real page before broader adoption.
- `@ant-design/pro-components` is not adopted because its current peer range does not target Ant Design 6.
