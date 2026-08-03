# IAM semantic change audit API test plan

All cases use a fresh isolated database whose name ends in `_test` or `_pytest`.
Use the existing authentication fixtures and never mutate the canonical
development database.

## Setup

- Provision a Platform Administrator and one target user.
- Create an active custom role with a known permission set and capture its ID.
- Run migrations and verify the `audit_event` table, Chinese table/column
  comments, three indexes, and JSONB-object check constraint.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Create role | Platform Administrator | `POST /api/v1/iam/roles` | Existing success response | One `iam.role.created` row with actor UUID, request ID, new role ID, code, and permission codes | No role description or request body in `changes` |
| E2E-002 | Update role state | Active custom role | `PATCH /api/v1/iam/roles/{id}` with `is_active` | Existing success response | One `iam.role.deactivated` or `iam.role.activated` row with exact boolean before/after | A name-only update uses `iam.role.updated` and records no free-text name |
| E2E-003 | Replace role permissions | Custom role with known permissions | `PUT /api/v1/iam/roles/{id}/permissions` | Existing success response | One `iam.role.permissions_replaced` row with before/after permission-code lists | No arbitrary payload fields in `changes` |
| E2E-004 | Replace user roles | Target user with known roles | `PUT /api/v1/iam/users/{id}/roles` | Existing success response | One `iam.user.roles_replaced` row with before/after role-ID lists | No user email or name in the row |
| E2E-005 | Delete inactive role | Inactive unassigned custom role | `DELETE /api/v1/iam/roles/{id}` | Existing success response | One `iam.role.deleted` row retains the deleted role ID | No FK prevents the deletion or removes the event |
| E2E-006 | Failed IAM mutation | Active role or invalid permission set | Existing failing request | Existing 400/403/409 `detail` plus `request_id` contract | No new `audit_event` row | Business transaction remains rolled back |
| E2E-007 | Retention and downgrade | Events at cutoff boundary | Call cleanup service and attempt migration downgrade | Cleanup returns deleted count; nonempty-table downgrade refuses | Only rows older than 365 days are deleted | Boundary/newer rows remain; downgrade never silently deletes evidence |

## Execution

- Run every case against the same backend selected by the isolated database and
  verify its health endpoint first.
- Assert every successful HTTP-created event stores the response
  `X-Request-ID` value, never a client-supplied audit field.
- Run the focused and full backend suites, then record any concrete environment
  blocker in `implement.md` rather than treating an unrun test as passed.
