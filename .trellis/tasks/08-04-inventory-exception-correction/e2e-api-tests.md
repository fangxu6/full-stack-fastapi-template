# Inventory Exception Correction API E2E Test Plan

## Environment

- Backend: `http://127.0.0.1:8000`
- Health: `/api/v1/utils/health-check/`
- Frontend: `http://localhost:5173`
- Use a dedicated test database and dedicated users. Never run these cases
  against a developer database.

## Cases

| ID | Endpoint / flow | Setup and request | Expected result |
| --- | --- | --- | --- |
| E2E-001 | Ordinary write guard | Use a non-legacy document with ledger rows. Call `PUT`, `DELETE`, and restore with `inventory.documents.manage`. | Each returns HTTP 409 with `detail: "INVENTORY_CORRECTION_REQUIRED"`, a body `request_id`, and `X-Request-ID`; document and ledger are unchanged. Create/import retain their existing behavior. |
| E2E-002 | Create request | `POST /api/v1/inventory/correction-requests` with target ID, operation, public `updated_at`, typed proposal, and reason. Caller has request permission. Also send unknown outer/nested fields, blank/oversized reasons, and timezone-naive timestamps. | `201 PENDING_REVIEW`; immutable canonical proposal/hash persists; ledger is unchanged. Invalid closed-DTO input, missing permission, stale token, unknown enum, wrong operation/proposal combination, or missing reason returns the unified 4xx response and creates no request. Concurrent creation for the same document has one success and one stable active-request 409, with no partial request. |
| E2E-003 | Review and one work item | Same user has request and review permissions. Call `POST /api/v1/inventory/correction-requests/{id}/approve`, then repeat and race it. Exercise `/reject` and `/withdraw` separately. | One approved request, one work item, and one `PENDING` initial attempt; no ledger effect. Rejection and withdrawal leave no work item or attempt. |
| E2E-004 | Successful automatic application | Run the correction executor for a pending work item. | Document, ledger, attempt, work item, request state, System Actor attribution, and successful audit event commit together. A repeated delivery has no second effect. |
| E2E-005A | Approval-time stale | Submit a request with an old `updated_at`, then approve it. | The committed typed response has request status `STALE`; no work item or attempt is created, and document/ledger remain unchanged. This state transition is not rolled back as an error. |
| E2E-005B | Executor-time stale and negative failure | Approve a current proposal, then use a trusted test fixture to advance the target `updated_at` before execution; separately queue a proposal that violates the negative-balance guard. | Each becomes `TERMINAL_FAILED` with `STALE_TARGET` or `NEGATIVE_BALANCE`; original document and ledger remain unchanged; no automatic retry is queued. The fixture mutation uses a bound audit actor because ordinary writes are correction-blocked. |
| E2E-006 | Lost lease and recovery | Simulate loss after claim before apply, expire the lease, then call `POST /api/v1/inventory/correction-work-items/{id}/recover` with an empty body. Also create another active request for the same document before recovery. | Lease loss is terminal without automatic apply. Recovery appends exactly one `PENDING` attempt and returns `202`; its next scheduler claim reuses that row. Concurrent recovery has one success and no duplicate attempt. An active-request conflict and changed timestamp return stable `409` responses with no state change. |
| E2E-007 | Authorization, pagination, UI, and redaction | Exercise request/review/recover permission combinations, including self-review, foreign-request detail/withdrawal, and paginated queue/list requests. Open the correction page from the document action as authorized and unauthorized users. | Only authorized queue/actions and details are visible; every list returns correct `data/count` and deterministic pagination; no manual apply action appears. Audit summaries contain only their fixed keys. Attempt rows retain failure categories; task logs contain no correction business IDs, proposal JSON, reason text, or exception text. |
| E2E-008 | Scheduler batch isolation | Queue two approved corrections; force the first into a controlled terminal failure. | The first work item/attempt becomes terminal, the second is processed, and the enclosing scheduler run succeeds. Manual run-now and backfill are unavailable for this task. |

## Execution Evidence

Record the command, response, database assertions, and any isolated-environment
blocker in the task validation notes after implementation.

### 2026-08-04 validation

- `POSTGRES_DB=aiadmin_test uv run pytest tests -q` passed: 322 passed, 2
  skipped. The isolated TestClient coverage exercises the correction request,
  direct-write, scheduler, recovery, audit, and permission paths.
- `uv run mypy app`, `uv run ty check app`, Ruff checks, focused Biome, Vite
  production build, and the correction-route AST check passed.
- Process-level E2E is blocked in this checkout: no service was listening on
  `127.0.0.1:8000` (`curl` connection refused). The frontend full build also
  stops on four unchanged `bun:test` type imports; Playwright lacks its browser
  binary. The project quality hook now passes with generated artifacts pending
  their required Phase 3.4 synchronization commit.
