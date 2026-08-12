# Workflow Capability Audit API/UI Validation Scope

## Environment

- Backend: `http://127.0.0.1:8000`
- Health: `/api/v1/utils/health-check/`
- Frontend: `http://localhost:5173`
- Isolation: a dedicated test database and dedicated users; never use a
  developer database.

## Current Inventory Evidence Cases

| ID | Flow | Setup / request | Expected response and persistence |
| --- | --- | --- | --- |
| WF-001 | Request and review | Use a ledger-affected document; create a typed correction request, then approve/reject/withdraw with permission combinations. | Immutable request; one approval work item and initial attempt; no ledger effect; duplicate/concurrent decisions are stable no-ops or conflicts. |
| WF-002 | Apply and failure | Execute a pending attempt with current, stale, negative-balance, duplicate-delivery, and lease-loss fixtures. | Success commits document, ledger, attempt, work item, request, System Actor, and audit together; failure is terminal with unchanged ledger and no automatic retry. |
| WF-003 | Recovery and authorization | Recover a terminal work item with unchanged target/hash; repeat concurrently and add another active request. | Exactly one recovery attempt; active-request or changed-target conflict leaves all rows unchanged; queue/detail/actions honor request, review, and recover permissions. |
| WF-004 | UI and redaction | Open the correction page from the inventory document list under each permission combination. | Only permitted tabs/actions and server-filtered data appear; no manual apply; audit summaries contain allowlisted keys and no raw reason/proposal/exception text. |

These cases are the completed child contract, not a new generic API. Their
full endpoint matrix and execution evidence remain in the archived child
`08-04-inventory-exception-correction/e2e-api-tests.md`.

## Future Comparison Cases

Before generalization, the second workflow must add:

| ID | Assertion |
| --- | --- |
| WF-005 | Its request/review or equivalent decision path has the same explicit actor, permission, duplicate-command, and terminal semantics, or documents the incompatibility. |
| WF-006 | Its durable work/attempt, lease, retry, recovery, and scheduler handoff can be tested without sharing inventory tables or handler payloads. |
| WF-007 | Its API/UI/operator surface preserves server authorization, generated-client synchronization, pagination/error contracts, and domain-local action capabilities. |
| WF-008 | Its audit/redaction/retention contract and failure side effects can be compared field-by-field with inventory. |

## Execution

Run the current cases only when the inventory child is revalidated in a future
implementation task. Run the comparison cases only after a second workflow is
approved and a separate promotion task owns product changes. Record commands,
responses, persistence assertions, and concrete environment blockers in that
task's validation notes.
