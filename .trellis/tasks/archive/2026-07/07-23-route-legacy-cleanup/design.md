# Route Legacy Cleanup Design

## Boundary

`frontend/src/routes/**` remains the file-based router adapter layer: route
declaration, search validation, guards, metadata, and imported page-component
references only. Route-aware page behavior belongs in the owning `platform`
page module.

## Search-State Ownership

`RulesPage` will read `slug` with `useSearch({ from: "/_layout/rules" })` and
`ResetPasswordPage` will read `token` with
`useSearch({ from: "/reset-password" })`. Their route files retain the Zod
schemas, so page values remain validated and typed. The route imports the page
directly, eliminating the adapter component and avoiding route-to-page import
cycles.

## Compatibility

There are no other callers of either page component. Their internal prop
interfaces can therefore be removed without a compatibility wrapper. The
route IDs, redirect behavior, titles, generated route tree, and backend calls
remain unchanged.

## Regression Protection

Extend the existing Bun AST checker tests to scan every current `.tsx` route
entry. The root checker exemption remains the single documented framework
exception; any future ordinary local route component fails the inventory test
and the changed-file quality hook.

## Rollback

Revert the page search-state migration and its inventory test together. No
database, API contract, or generated artifact rollback is needed.
