# 分阶段缓存机制 API E2E Test Plan

## Environment

- Test-only FastAPI app: `backend/tests/api/test_request_unit_of_work.py`
- Production API changes: none; no cache endpoint is registered.
- Isolation: test double `TrackingSession` and mocked Redis cache primitive;
  no development PostgreSQL data or Redis keyspace is modified.

## Cases

| ID | Endpoint / Flow | Setup Data | Request | Expected Response | Persistence / Side Effects | Failure Assertions |
| --- | --- | --- | --- | --- | --- | --- |
| E2E-001 | `POST /__test/cache-commit` on the test-only FastAPI app | Override `get_db` with `TrackingSession`; register one `cache:v1:test:one` invalidation; mock delete | Empty POST | `200` and success body | Event order is `open`, `commit`, `cache_delete`, `close`; mocked delete receives only the registered key | No delete occurs before commit |
| E2E-002 | `POST /__test/cache-rollback` on the test-only FastAPI app | Same override and registered key; handler raises `HTTPException(409)` | Empty POST | `409` | Event order is `open`, `rollback`, `close` | Cache delete is never called |
| E2E-003 | Cache client outage through its direct integration test | Mock Redis read/write/delete to raise a connection error | Call cache primitive, not a public endpoint | No exception escapes | Read is a miss; write/delete are no-ops; safe error telemetry is emitted | No key/value/URL/exception text reaches telemetry |

## Execution

- E2E-001 and E2E-002 run with the focused backend pytest command in
  `implement.md`; they validate the FastAPI dependency lifecycle without
  adding a production-only test route.
- E2E-003 is a direct core integration test because this iteration deliberately
  exposes no cache HTTP API.
- Do not claim a local `localhost:8000` cache endpoint test: no such endpoint
  exists in the approved scope.
