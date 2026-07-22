# RBAC API E2E Test Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `GET /api/v1/utils/health-check/`
- Browser target: `http://localhost:5173`
- Isolation: run against the backend test database configured for `uv run
  pytest`; do not seed or mutate a development database. For local HTTP E2E,
  start a dedicated backend instance pointed at an isolated PostgreSQL database
  created for this task.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Migration and bootstrap | Existing legacy superuser plus normal user; seeded first-superuser on empty DB; a deliberately incomplete IAM seed state. | Run migration and initialization twice. | Migration and repeated initialization succeed. | Every legacy superuser has `platform_administrator`; normal users have no role; all catalog and built-in baseline rows exist; the configured first superuser has the platform role; custom-role rows are unchanged. | No duplicate role assignments, missing baseline, or normal-user assignment. |
| E2E-001a | No-admin startup recovery | IAM seed complete but every Platform Administrator User inactive or unassigned. | Run initialization. | Startup fails with a credential-free high-priority diagnostic. | No User becomes active and no new assignment is written. | No implicit recovery, token, password, or personally identifying data appears in logs. |
| E2E-002 | `GET /api/v1/iam/me/permissions` | Platform admin, inventory operator, inventory viewer, and zero-role user. | One authenticated request per user. | `200` with only active role summaries and exact effective codes. | Read only. | Zero-role result has empty roles/permissions; inactive role does not appear. |
| E2E-003 | Custom role CRUD | Platform admin and permission catalog. | Create custom role, update description, replace permission set, deactivate, reactivate, unassign, delete; inspect editor catalog presentation. | Success for valid lifecycle transitions. | Role code immutable; selecting an inventory manage permission visibly persists its read prerequisite; Governance Permissions are visible but disabled with a built-in-role explanation; assignments survive deactivate/reactivate; delete removes only unassigned inactive role. | Duplicate code `409`; missing inventory prerequisite `422` or conflict with unchanged role state; any `system.users.*` or `iam.roles.*` code in a custom role `422` or conflict with unchanged role state; built-in edit/delete `403` or conflict; active/assigned delete leaves rows unchanged. |
| E2E-004 | User role assignment | Two active platform admins, target user, custom role. | `PUT /api/v1/iam/users/{id}/roles`. | `200` with updated role summaries. | Assignment replacement is atomic and affects the target's next request. | Inactive role assignment `409`; request removing final active platform admin `409`; role rows/assignments unchanged on failure. |
| E2E-005 | User administration authorization | Platform admin, inventory operator, zero-role user, active and inactive roles. | List/create/update/deactivate users and replace roles; create a user with valid and invalid `role_ids`; send `role_ids` to public signup. | Platform admin succeeds for allowed writes; public signup succeeds only without role IDs. | A valid admin create atomically persists the user and selected assignments. | Other callers receive `403` with `detail` and `request_id`; invalid/inactive role IDs leave no user or assignments; public signup role input receives `422`. |
| E2E-006 | Inventory read permissions | Operator, viewer, zero-role user, a balances-only custom role, and inventory fixtures containing creator/updater IDs, import associations, and remarks. | Read masters, documents, balances, ledger; open a balance row in the browser for roles with and without ledger read. | Operator and viewer succeed and receive the current complete public field set; a balances-only role sees balances but no related-ledger entry; zero-role user denied. | Read only. | Each denial is `403` with `detail` and `request_id`; ledger API independently rejects balances-only callers; no role-specific redaction is implied by frontend presentation. |
| E2E-007 | Inventory management permissions | Operator, viewer, document/master fixtures, documents created by another user, and a historical import document. | Create/update master; create/update/delete/restore own, other-user, and historical documents through both raw-material and finished-shipment pages; editor suggestions. | Operator succeeds for every document source and both page types under the shared document permission pair. | Allowed mutations persist; restore behavior remains correct. | Viewer and zero-role callers get `403`; target rows and ledger effects remain unchanged. |
| E2E-008 | Legacy compatibility | Legacy superuser and normal user with Item and AI fixtures. | Existing Item and AI requests. | Existing behavior is unchanged. | No IAM role assignment changes legacy behavior. | No new RBAC permission is required for deferred endpoints. |
| E2E-009 | Frontend authorization flow | Viewer and zero-role browser sessions; delayed, `401`, unexpected `403`, and `5xx` own-permissions responses. | Navigate menus; direct visit allowed and denied `/inventory/*` and `/admin/*` routes; exercise return targets including internal path/search, `//host`, full URL, and `javascript:`; simulate each permission-query state. | Menus filter correctly; direct denied routes render forbidden page with return action; valid internal target returns there and invalid/missing target returns to `/`; pending/loading, login, retryable error, configuration error, and successful denial remain distinct. | Read only. | Protected API actions still return `403`; no hidden menu is treated as enforcement or an external redirect source; failed authorization fetch never renders protected content. |

## Execution

1. Verify the health endpoint against the selected isolated backend.
2. Run focused IAM, user, inventory, and exception-contract tests before local
   HTTP cases.
3. Run E2E-001 through E2E-008 against the isolated backend, then E2E-009
   against the isolated frontend/backend pair.
4. Record executed commands, results, and any concrete environment blocker in
   the task validation notes before implementation is marked complete.
