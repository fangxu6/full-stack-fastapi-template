# Legacy Directory Inventory

## Scope Baseline

The active frontend ownership model is `app`, `platform`, `features`,
`shared`, and thin `routes`. This task retires `components`, `hooks`, `lib`,
and the root `utils.ts` file without changing runtime behavior.

| Legacy surface | Verified contents | Final owner |
| --- | --- | --- |
| `components/ui` | 24 shadcn/ui vendor-style primitives | `shared/components/ui` |
| `components/theme-provider.tsx` | Theme context, provider, and hook | `shared/components/theme/ThemeProvider.tsx` |
| `components/Pending/*` | Item/user table skeleton implementations | Existing `shared/components/feedback/*TableSkeleton` files |
| `hooks/useAuth.ts` | Login, logout, signup, token, and current-user behavior; 14 callers | `platform/auth/hooks/useAuth.ts` |
| Other `hooks/*` | Clipboard, toast, and mobile helpers | `shared/hooks` |
| `lib/utils.ts` and root `utils.ts` | `cn`, `handleError`, and `getInitials` helpers | `shared/utils` |

## Dependency And Tooling Evidence

- Sixty-five frontend files import at least one legacy alias. Consumers span
  app, platform, features, shared, routes, and the bootstrap entrypoint.
- The Pending implementations each have one caller, their existing shared
  feedback skeleton entrypoint. Replacing the re-export files with the moved
  implementations removes an unnecessary indirection.
- `frontend/components.json` currently maps `components`, `ui`, `hooks`,
  `lib`, and `utils` aliases to the legacy tree.
- `frontend/biome.json`, `hooks/quality_hooks/frontend.py`, and
  `hooks/tests/test_quality_hooks.py` currently protect or test the old
  vendor-style primitive location.
- Active frontend specs and `frontend/ARCHITECTURE.md`,
  `frontend/CODING_STANDARDS.md`, and `frontend/README.md` still document the
  old paths.

## Decisions

- Retain the existing shadcn/ui primitive source; do not replace it with Ant
  Design.
- Move the root `utils.ts` file in the same change, so `shared/utils` becomes
  the only generic utility entrypoint.
- Do not retain alias compatibility layers or empty legacy directories.
