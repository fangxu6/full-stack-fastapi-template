# Design: Frontend Legacy Directory Refactor

## Ownership Map

| Current | Final | Rationale |
| --- | --- | --- |
| `components/ui/**` | `shared/components/ui/**` | Reusable shadcn/ui primitives remain vendor-style source. |
| `components/theme-provider.tsx` | `shared/components/theme/ThemeProvider.tsx` | Theme state is shared by bootstrap, app, and shared presentation components. |
| `components/Pending/PendingItems.tsx` | `shared/components/feedback/ItemsTableSkeleton.tsx` | The existing shared entrypoint is its sole consumer. |
| `components/Pending/PendingUsers.tsx` | `shared/components/feedback/UsersTableSkeleton.tsx` | The existing shared entrypoint is its sole consumer. |
| `hooks/useAuth.ts` | `platform/auth/hooks/useAuth.ts` | It owns authentication-session behavior, not generic React behavior. |
| Remaining `hooks/*` | `shared/hooks/*` | They provide domain-neutral browser/UI behavior. |
| `lib/utils.ts` and `utils.ts` | `shared/utils/index.ts` | They provide generic styling and display/error helpers. |

The final utility entrypoint exports the existing symbols without changing their
semantics. Consumers use final aliases rather than retained aliases at the
legacy locations.

## Tooling And Documentation Contract

- Update `components.json` so shadcn resolves `components`, `ui`, `hooks`,
  `lib`, and `utils` into the final shared paths.
- Move the Biome vendor-style exclusion and the frontend quality hook's
  vendor-managed path to `shared/components/ui`. Remove the retired
  `components` component root and update focused tests to assert the new path.
- Update active frontend specs and repository-local frontend documents to list
  the final tree and final code anchors. Historical task archives remain
  historical evidence and are not rewritten.

## Compatibility

This is an atomic source-path migration. Public component exports, hook
behavior, theme storage key, route declarations, generated client, and API
contracts do not change. No compatibility re-exports remain after the import
rewrite, because the task's outcome includes deleting the legacy roots.

## Risks And Rollback

- A missed import or stale generator alias fails type-check/build. Mitigate
  with targeted searches, the read-only Biome check, and `bun run build`.
- Moving the vendor-style directory without its policy update could weaken
  edit protection. Mitigate with focused hook tests and an explicit hook run.
- A behavior regression is unlikely because implementations are moved rather
  than rewritten; validate auth routes and shell rendering with Playwright.
- Roll back the path migration and configuration/doc updates together. Do not
  retain only one side of the old/new alias contract.
