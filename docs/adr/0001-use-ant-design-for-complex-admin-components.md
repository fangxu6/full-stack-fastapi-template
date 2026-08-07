# Use Ant Design for Complex Admin Components

## Status

Accepted. Ant Design is the default component system for new data-dense
business-management surfaces, with the existing shadcn/ui layer retained for
the explicitly listed cases below.

## Context

The frontend already has a working Tailwind + shadcn/ui primitive layer. The
repository also installs Ant Design 6 and mounts its provider in
`frontend/src/app/providers/AntdProvider.tsx`; the Rules page is a real usage
example. A full replacement would create unnecessary migration risk.

## Decision

- Use `antd` directly in new data-dense workflows under `features/*` or
  `platform/*`, including dense tables, filter/search forms, forms, date and
  selection controls, dialogs, and loading/empty/error feedback.
- Keep existing shadcn/ui primitives for the app shell, authentication, simple
  dialogs, and already-working pages. Do not migrate them without a scoped
  payoff.
- Keep provider and token wiring in `app/providers/*`; do not create a global
  wrapper around every Ant Design component.
- `shared/excel` is the explicit shared exception that may import Ant Design;
  other `shared/*` code remains free of Ant Design.
- Do not adopt `@ant-design/pro-components` until its peer range and project
  need are reviewed in a dedicated decision.

## Considered Options

- Keep shadcn/ui only: lowest dependency cost, but leaves complex enterprise UI patterns to local composition.
- Adopt Ant Design for complex admin components: gives richer tables, lists, feedback, empty states, and form/page patterns without forcing a full migration.
- Replace shadcn/ui with Ant Design: higher visual consistency long term, but too much regression risk for the current app.

## Consequences

- The app may temporarily use both shadcn/ui primitives and Ant Design components.
- Ant Design usage is documented in the frontend component specification and
  verified through a real page before broader adoption.
- `@ant-design/pro-components` is not adopted because its current peer range does not target Ant Design 6.

## Related Decisions

- The frontend boundary is maintained in the
  [component guidelines](../../.trellis/spec/frontend/component-guidelines.md);
  no other ADR supersedes or narrows this decision.
