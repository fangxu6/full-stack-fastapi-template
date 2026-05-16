# Route Permission Navigation Contract

> Executable contract for page placement, route guards, menu visibility, and permission entrypoints on the frontend.

## Scenario: Route, Permission, and Navigation Synchronization

### 1. Scope / Trigger

- Trigger: any change that does one or more of the following:
  - adds a new page
  - adds or changes a protected route
  - adds, removes, or renames a menu item
  - changes `app/router/guards.ts`
  - changes `shared/permissions/*`
  - moves a page between `routes/*`, `platform/*`, and `features/*`
- Primary files:
  - [`frontend/src/routes/_layout.tsx`](../../../frontend/src/routes/_layout.tsx)
  - [`frontend/src/routes/_layout/admin.tsx`](../../../frontend/src/routes/_layout/admin.tsx)
  - [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx)
  - [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts)
  - [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts)
  - [`frontend/src/app/navigation/AppSidebar.tsx`](../../../frontend/src/app/navigation/AppSidebar.tsx)
  - [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
  - [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx)
  - [`frontend/src/platform/system/pages/AdminUsersPage.tsx`](../../../frontend/src/platform/system/pages/AdminUsersPage.tsx)
  - [`frontend/src/features/items/pages/ItemsPage.tsx`](../../../frontend/src/features/items/pages/ItemsPage.tsx)

### 2. Signatures

- Route entry files:
  - `routes/*.tsx`
  - `routes/_layout/*.tsx`
- Guard entrypoints:
  - `requireLogin(): Promise<void>`
  - `requireSuperuser(): Promise<void>`
- Permission entrypoint:
  - `canAccessAdmin(user): boolean`
- Navigation entrypoints:
  - `baseMenuItems: AppNavigationItem[]`
  - `adminMenuItem: AppNavigationItem`
  - `getMenuItemsForUser(user): AppNavigationItem[]`

### 3. Contracts

- `routes/*` must remain thin route-entry files. They may define:
  - `Route`
  - `beforeLoad`
  - `head()`
  - page-module imports
  They must not become the long-term home of full page implementation.
- Real page implementations must live under:
  - `platform/*/pages` for platform capabilities
  - `features/*/pages` for business features
- Protected access must be enforced through `app/router/guards.ts`, not through ad hoc page-level redirect logic.
- Menu visibility must be derived from centralized navigation config and shared permission helpers:
  - guards decide route access
  - `shared/permissions/*` decides permission truth
  - `app/navigation/*` decides visible menu structure
- When a route requires a permission rule, the route guard path and the menu-visibility path must stay aligned. Do not let a route remain reachable while the menu hides it for a different reason, or vice versa, unless that asymmetry is intentional and documented.
- New pages must be classified before placement:
  - app-shell concern -> `app/*`
  - platform capability -> `platform/*`
  - business feature -> `features/*`
- `shared/*` is not a page-placement layer and must not absorb whole pages or route orchestration.

### 4. Validation & Error Matrix

| Condition | Expected behavior |
| --- | --- |
| add public auth page | thin route imports page module from `platform/auth/pages/*`; route may redirect logged-in users in `beforeLoad` |
| add protected page under existing authenticated layout | route is attached under protected layout or guarded with `requireLogin` |
| add admin-only page | route uses `requireSuperuser`; menu visibility derives from `canAccessAdmin` path |
| add menu item | `menu-config.ts` and actual route path stay synchronized |
| move page implementation | route file remains thin; implementation lands in `platform/*/pages` or `features/*/pages` |
| change permission truth | `shared/permissions/*`, guards, and menu visibility all remain aligned |
| page only exists in route file | invalid; page implementation must be extracted to a page module |
| menu item points to no reachable route | invalid unless intentionally staged and documented |

### 5. Good / Base / Bad Cases

- Good: [`frontend/src/routes/login.tsx`](../../../frontend/src/routes/login.tsx) stays thin and delegates to [`frontend/src/platform/auth/pages/LoginPage.tsx`](../../../frontend/src/platform/auth/pages/LoginPage.tsx).
- Good: [`frontend/src/routes/_layout/admin.tsx`](../../../frontend/src/routes/_layout/admin.tsx) protects admin access through [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts), while menu visibility uses [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts) via [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts).
- Base: a new authenticated business page is added under `routes/_layout/*` and points to a page module in `features/*/pages`, with no extra menu item because the page is intentionally deep-linked only.
- Bad: a new page is fully implemented in `routes/reports.tsx` because it was faster than creating `platform/reports/pages/ReportsPage.tsx`.
- Bad: an admin menu item is added in `menu-config.ts` but the route forgets to use `requireSuperuser`.
- Bad: route access checks `is_superuser` inline while the menu still uses `canAccessAdmin`, creating two permission truths.

### 6. Tests Required

- Structural verification:
  - confirm any new route file is still thin and delegates to a page module
  - confirm any new page module is placed in `platform/*/pages` or `features/*/pages`
- Permission verification:
  - confirm guard logic in [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts) stays aligned with [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts)
  - confirm menu visibility from [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts) matches expected route access
- Validation commands:
  - run `bun run lint`
  - run `bun run build` when the change affects routes, types, imports, or page placement
- UI regression checks when relevant:
  - protected route still redirects correctly
  - admin route stays hidden or shown consistently with user permissions
  - navigation still renders the expected menu items

### 7. Wrong vs Correct

#### Wrong

- Build the whole page in `routes/*.tsx`.
- Put a business page under `shared/*` because more than one route might someday link to it.
- Add a menu item without adding or validating the matching route.
- Add a route guard inline in one route while permission truth is defined somewhere else.
- Check permissions in page components as the primary long-term control path.

#### Correct

- Keep route files thin and delegate to page modules.
- Place pages in `platform/*/pages` or `features/*/pages` based on ownership.
- Keep guard logic centralized in [`frontend/src/app/router/guards.ts`](../../../frontend/src/app/router/guards.ts).
- Keep permission truth centralized in [`frontend/src/shared/permissions/index.ts`](../../../frontend/src/shared/permissions/index.ts).
- Keep navigation visibility centralized in [`frontend/src/app/navigation/menu-config.ts`](../../../frontend/src/app/navigation/menu-config.ts) and consumed through [`frontend/src/app/navigation/AppSidebar.tsx`](../../../frontend/src/app/navigation/AppSidebar.tsx).
