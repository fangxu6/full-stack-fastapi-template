# IAM audit remediation API test plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: an empty PostgreSQL database ending in `_test` or `_pytest`; do
  not write fixtures to the development database.
- Authentication: an existing Platform Administrator token with
  `iam.roles.manage`.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Concurrent permission replacements | Active custom role with `[P1]`; two isolated service transactions | First requests `[P2]`; second requests `[P3]` while first holds the role lock | Both replacements eventually succeed | Final permission set is `[P3]`; audit events are `[P1] -> [P2]` then `[P2] -> [P3]` | The second transaction cannot read stale `[P1]` or leave a mixed set |
| E2E-002 | Empty role PATCH | Existing custom role and captured `updated_at`/event count | `PATCH /api/v1/iam/roles/{id}` with `{}` and a known request ID | 422 with `detail`, `request_id`, and matching `X-Request-ID` | Role and audit-event count stay unchanged | No role timestamp, permission link, or semantic event is persisted |
| E2E-003 | Same-value role PATCH | Existing custom role and captured state | PATCH an existing `name`, `description`, or `is_active` value | 422 with the shared error envelope | Role and audit-event count stay unchanged | No false `changed_fields` or state-transition event exists |
| E2E-004 | Real role PATCH | Existing custom role | PATCH a changed display name or state | Existing 200 role response | One `iam.role.updated` or state event uses only actual changed fields | Existing response payload and request-ID behavior remain intact |

## Execution

- Verify the isolated backend health endpoint before live API execution.
- Run the focused pytest cases as the automated primary proof.
- Record any concrete local-server or isolated-database blocker in
  `implement.md`; do not treat an unrun E2E case as passed.
