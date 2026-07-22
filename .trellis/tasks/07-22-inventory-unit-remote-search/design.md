# Inventory Unit Remote Search Design

## Boundary And Contract

The frontend feature-local API wrapper already exposes the required request
contract. No backend or generated-client change is needed. A domain-local
React hook will own remote unit option state so the four Ant Design Select
instances do not duplicate debounce, query-key, and result mapping logic.

The hook accepts a unit kind and an active-state scope. It requests
`skip=0, limit=20`, adds `name` for the debounced search term, and includes the
kind, active-state scope, and effective term in its React Query key. Results
remain a page slice; the UI does not implement `onPopupScroll` or accumulate
additional pages.

## UI Behavior

Each Select uses `showSearch`, `filterOption={false}`, and the hook's search
callback. Empty input loads the default 20 options. A 300 ms debounce changes
the effective query; loading uses Select's dropdown loading content and an
empty successful response uses its normal empty content. The active request's
options are the only results rendered, and the selected option is retained in
the local option set while another term is loading.

Document filters pass no `is_active` predicate, which keeps historical filters
complete. The document editor passes `is_active=true`, matching the existing
write-time service rule. The editor does not change handling for documents
whose current unit has since been deactivated.

## Compatibility And Documentation

Existing URLs, response DTOs, database schema, and server validation remain
unchanged. Add a short frontend-spec rule that large business Selects must use
server-side search instead of loading a fixed first page for client filtering.

## Rollback

Revert the frontend hook and Select integrations. The API and persisted data
are unaffected.
