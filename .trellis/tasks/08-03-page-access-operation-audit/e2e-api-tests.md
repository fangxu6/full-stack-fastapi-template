# IAM audit API and cross-layer test plan

All API cases use a fresh isolated database whose name ends in `_test` or
`_pytest`. Use the existing test authentication fixtures and never mutate the
canonical development database.

## Setup

- Provision a Platform Administrator, an IAM read-only user, and a user with
  no IAM role-management permission.
- Create one active custom role and one target user with a known role
  assignment. Capture their UUID/IDs for assertions.
- Run migrations and verify the `audit_` table, enum types, comments, and
  indexes before the request cases.

## API cases

### 1. Successful IAM page access

- Request the page-access endpoint as the IAM reader for `iam_roles` and
  `iam_users` with outcome `succeeded`.
- Assert `201`, server-bound actor UUID, `page_access` event type,
  `frontend_route_guard` source, correct page code, and no PII fields.
- Query as Platform Administrator and assert both rows are visible.

### 2. Frontend route-guard denial

- Submit a denied `iam_roles` page event as the authenticated no-role user.
- Assert the event is stored as `page_access` / `frontend_route_guard` /
  `denied` with `frontend_guard_denied` result code and the actor UUID.
- In the frontend guard test, verify the event call is best-effort and the
  user still redirects to `/forbidden` when the call fails.

### 3. Backend permission denial

- Call an IAM mutation endpoint as the no-role user.
- Assert the normal `403` detail/request-ID contract is unchanged.
- Query as Platform Administrator and assert one authoritative
  `authorization` / `backend_permission` / `denied` event with permission code,
  route template, actor UUID, resource ID when available, and no request body.

### 4. Successful privileged operations

- Create a role, update/deactivate it, replace its permission codes, and
  replace a target user's roles as Platform Administrator.
- Assert each business response succeeds and exactly one
  `privileged_operation` / `backend_operation` / `succeeded` event is committed
  atomically with the change.
- Assert summaries contain only allowlisted IDs/codes/scalars.

### 5. Failed authorized operations

- Attempt to delete an active role, submit an invalid role permission set, and
  violate the active Platform Administrator invariant.
- Assert the normal `409`/`400` response is returned and the business
  transaction is rolled back.
- Query audit rows and assert one `failed` event per attempt with only the
  operation, resource ID, and stable result code. Assert the event remains
  after rollback and has no rejected input or free text.

### 6. Query authorization and filters

- Assert an IAM reader and no-role user receive `403` from
  `GET /api/v1/audit/events`.
- Assert Platform Administrator receives paginated results and filters by
  source, outcome, operation, actor, resource, permission, and UTC time window.
- Assert deleted users/roles leave readable identifiers and do not make the
  query fail.
- Assert no export route is present in OpenAPI and an attempted export path is
  rejected.

### 7. Retention cleanup

- Insert events exactly at, just inside, and just outside the 365-day cutoff.
- Run `cleanup_expired_events(now)` directly and through the registered
  scheduler task. Assert only rows older than the cutoff are deleted, the
  operation is idempotent, and newer rows remain queryable.

### 8. Migration and rollback

- Upgrade an empty isolated database and assert enum values, table/index names,
  Chinese comments, and column types.
- Insert an event, attempt downgrade, and assert the downgrade refuses rather
  than deleting evidence. After an explicit empty-table setup, assert
  downgrade removes the table and enum types in dependency order.

## Cross-layer verification

- Regenerate the frontend client from the final OpenAPI schema and assert the
  generated audit types/services are the only generated changes.
- Render `/admin/roles`, `/admin`, and `/admin/audit` with a signed-in browser
  session. Verify successful page events, denied redirects, query pagination,
  and the absence of an export control.
- Run the full backend suite and frontend lint/type checks on fresh isolated
  state before activation or commit.
