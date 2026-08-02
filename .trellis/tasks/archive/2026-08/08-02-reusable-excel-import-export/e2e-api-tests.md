# Excel Import/Export E2E API Test Plan

## Environment

- Target backend: `http://127.0.0.1:8000`
- Health check: `/api/v1/utils/health-check/`
- Isolation: `POSTGRES_DB=aiadmin_test`; never use development data.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `GET /api/v1/inventory/excel/templates/documents` | User with document-manage grant | Authenticated request | 200 XLSX attachment | None | Missing grant returns 403 |
| E2E-002 | `POST /api/v1/inventory/excel/imports/documents` | Active processing/receiving units | Valid multipart flattened workbook | 201 import report | Grouped documents, lines, and ledgers commit | No authorization returns 403 |
| E2E-003 | Standard import validation | Same as E2E-002 | Workbook with invalid cell/group | 422 with `detail.issues` and `request_id` | No created documents or ledgers | Issue includes sheet/row/column/field |
| E2E-004 | `POST /api/v1/inventory/excel/imports/legacy` | Active importing user and legacy fixtures | Raw plus finished multipart workbooks | 201 batch report | Existing fingerprinted batch and history rows commit | Invalid legacy row returns structured 422 and no batch |
| E2E-005 | `GET /api/v1/inventory/excel/ledger` | Raw and finished ledger fixtures | Ledger kind with optional unit/date filters | 200 XLSX attachment | None | Missing ledger-read grant returns 403; filter excludes nonmatching rows |

## Execution

- Verify the health endpoint against the isolated local backend.
- Execute the cases after implementation and record any concrete runtime
  blocker in this task's validation notes.

## Recorded Result (2026-08-02)

- The TestClient route coverage executed E2E-001 through E2E-005 against
  `aiadmin_test`, including multipart uploads, permissions, full rollback,
  legacy row issues, and raw/finished ledger downloads.
- No running standalone backend was required; the application was exercised
  through its FastAPI request stack. Two optional tests that require local real
  legacy workbook fixtures were skipped.
