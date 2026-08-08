# E2E API Test Plan: 主从数据库读写依赖预留

本 task 只定义应用依赖边界；真实 PostgreSQL 主从复制和读库部署不在测试范围内。
测试使用未配置 `POSTGRES_READ_REPLICA_SERVER` 的隔离测试环境，验证读依赖回退到同一
主库 engine 的兼容行为。

## E2E-001: No Replica Preserves Read Behavior

| Field | Expectation |
| --- | --- |
| Setup | `POSTGRES_READ_REPLICA_SERVER` unset; isolated test database available |
| Request | Call one migrated scheduler or inventory GET endpoint |
| Response | Existing status code and response body contract remain unchanged |
| Persistence | No database writes and no commit event from the read dependency |
| Failure side effect | No connection to a second database and no fallback logic invoked |

## E2E-002: Read Dependency Uses Read Engine Contract

| Field | Expectation |
| --- | --- |
| Setup | Override `get_read_db()` with a tracking Session in a small FastAPI test app |
| Request | Call an endpoint annotated with `ReadSessionDep` |
| Response | Endpoint returns normally using the yielded Session |
| Persistence | Session is opened and closed once; commit and rollback are not called |
| Failure side effect | Endpoint exception closes the Session and does not trigger write transaction handling |

## E2E-003: Write Dependency Remains Primary Transaction Owner

| Field | Expectation |
| --- | --- |
| Setup | Existing tracking Session and `WriteSessionDep` override |
| Request | Call a representative POST/PUT/PATCH/DELETE endpoint |
| Response | Existing success or domain-error response remains unchanged |
| Persistence | Successful request commits once; failed request rolls back once before close |
| Failure side effect | No `ReadSessionDep` or read engine is involved |

## E2E-004: Authentication and Permission Stay on Primary Session

| Field | Expectation |
| --- | --- |
| Setup | Authenticated request to a migrated read endpoint with its existing permission dependency |
| Request | Call the endpoint with valid bearer credentials |
| Response | Authentication and permission checks retain the current result |
| Persistence | Auth/permission dependencies use `SessionDep`; business query uses `ReadSessionDep` |
| Failure side effect | A read dependency change does not bypass or weaken authorization |

## E2E-005: No Automatic Primary Fallback Contract

| Field | Expectation |
| --- | --- |
| Setup | Configure a deliberately unavailable read host in an isolated test only |
| Request | Call a migrated read endpoint |
| Response | Existing database connectivity error handling is returned; no success response from primary |
| Persistence | No write is issued to the primary as a fallback |
| Failure side effect | The failure remains observable for later read-replica health monitoring |

## Execution Boundary

These cases are to be executed only after the implementation task is started. The current
task-generation operation creates this test plan but does not start services or run API tests.
