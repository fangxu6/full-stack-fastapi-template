# Route Quality Policy Design

## Boundary

`routes/*` remains the file-based router adapter layer. Page implementations
belong in `app`, `platform/*/pages`, or `features/*/pages`; the quality hook
enforces this boundary only for changed files so unrelated legacy code does
not block normal work.

## AST Policy

A Bun-executed script uses the frontend's installed TypeScript compiler API to
inspect route source files. For ordinary route files, it reports:

- a local PascalCase function or variable declaration;
- an inline arrow function or function expression assigned to `component`,
  `errorComponent`, or `notFoundComponent`.

`routes/__root.tsx` is exempt from those two route-shape checks because its
existing callbacks build the Router shell rather than a business page. All
other frontend quality policies remain in the Python hook.

## Integration

The Python frontend hook filters deleted paths before policy evaluation, then
passes existing route paths to the AST script in one process. Script findings
are added to the regular hook violation list. A script execution failure is a
quality failure with a diagnostic instead of silently allowing the route.

## Dashboard Migration

Move `Dashboard` into `frontend/src/platform/dashboard/pages/DashboardPage.tsx`.
The existing index route imports it and retains only route configuration and
metadata. No route topology changes, so generated output remains untouched.
