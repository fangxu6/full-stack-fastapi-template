# API E2E Test Plan: Validation Error Request ID

## Environment

- Test target: FastAPI `TestClient` against the application factory.
- Isolation: `POSTGRES_DB=aiadmin_test`; the repository test fixture rejects
  non-isolated databases.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | Validation error contract | None | `GET /__test/validation` without required `value` | `422` with `detail` array and `request_id` string | No persisted mutation | `X-Request-ID` equals body `request_id` |
| E2E-002 | Published validation schema | None | `GET /api/v1/openapi.json` | `HTTPValidationError.request_id` is required `string` | No persisted mutation | Existing `detail` array schema remains present |

## Execution Record

Executed through `uv run pytest tests/api/test_platform_baseline.py -q` with
`POSTGRES_DB=aiadmin_test`: 8 passed.
