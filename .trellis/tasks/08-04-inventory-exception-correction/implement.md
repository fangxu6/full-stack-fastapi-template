# Inventory Exception Correction Implementation Plan

## Gate

Do not run `task.py start` until the revised PRD, design, and E2E plan are
reviewed. This plan intentionally implements one inventory flow and no generic
workflow runtime.

## Ordered Checklist

1. Add the three correction permissions, their read prerequisites, and seed
   grants for Inventory Operator and Platform Administrator. Add `updated_at`
   to `InventoryDocumentPublic` and generated client contracts. Add the
   correction-page/menu entry using the existing `inventory.documents.read`
   route and menu permission.
2. Add the namespaced correction-request, work-item, and attempt models plus
   the additive migration. Use BIGINT identity, AuditFields, Chinese comments,
   named PostgreSQL enums, JSON-object checks, immutable target/proposal
   fields, unique request/work-item/attempt constraints, a partial active
   request constraint, and pending-queue indexes. Keep scheduler-run ID as a
   scalar value, not a foreign key.
3. Put the ledger-affected-document gate in the shared inventory write service.
   Ordinary update, delete, and restore return the stable correction-required
   conflict; create/import paths do not change. Add one internal
   `apply_approved_correction` path rather than a bypass flag.
4. Implement request create, list/detail, approve, reject, and withdraw with
   row locking, expected-`updated_at` checks, request-state guards, and one
   unique work-item creation transaction. Use the closed, operation-dependent
   request schema with `extra="forbid"` at nested boundaries, a trimmed
   nonblank bounded reason, and timezone-aware timestamps; hash only the
   normalized typed proposal with canonical stdlib JSON/SHA-256. Map concurrent
   active-request unique conflicts to the stable 409 error contract. Queue
   lists use `skip`/`limit`, `{ data, count }`, and deterministic ordering. Do
   not implement drafts, revisions, assignments, evidence storage, or
   cancellation. Mutation routes use `AuditedWriteSessionDep` and never commit
   directly. Approval-time staleness is returned as a committed typed `STALE`
   result, not raised after mutation, so the state transition is not rolled
   back.
5. Add one inventory correction executor task to the existing scheduler
   registry/bootstrap. It has empty config, runs every minute, disallows
   run-now/backfill, and claims at most 20 pre-created pending attempts. Use
   separate failure finalization for rollback cases. Its local session binds
   `context.actor_id` and clears it in `finally`; Celery receives only the
   scheduler run ID. Lease expiry becomes terminal failure, never automatic
   reapplication; one terminal item does not fail the scan batch.
6. Implement the one inventory handler branch by reusing the existing document
   service and ledger guard inside the executor transaction. Bind the existing
   System Actor. Do not add a handler protocol, registry, or external effect.
7. Add the empty-body recovery endpoint. It locks the terminal work item,
   checks the document timestamp and proposal hash, appends one `PENDING`
   attempt, and returns it to the pending queue. Before changing state, reject
   another active request for the same document with the stable 409 contract;
   the failed request and attempts remain unchanged. The scheduler claims that
   row; it never appends a second recovery attempt.
8. Add inventory-local correction audit action allowlists and fixed summary
   mappings. Keep failure evidence in the attempt row; do not extend the task
   log facade or build an audit query API.
9. Add one inventory-correction page with request, review, and recovery tabs.
   Reuse the inventory feature structure and generated client; enforce the
   detail/queue access matrix server-side, hide tabs/actions by permission, and
   do not expose manual application.
10. Run migration checks, focused backend/frontend tests, client generation,
   quality hooks, and the E2E cases below in an isolated environment. Review
   generated client and route-tree diffs; follow the repository's dedicated
   synchronization-commit workflow for generated outputs.

The deferred D-007 work is registered in
[deferred-iterations.md](./deferred-iterations.md); do not implement it here.

## Required Validation

- `cd backend && POSTGRES_DB=aiadmin_test uv run pytest tests/modules/inventory tests/modules/scheduler tests/api`
- `cd backend && bash scripts/lint.sh`
- `python hooks/run_quality_hooks.py --json`
- `bash ./scripts/generate-client.sh`
- `cd frontend && bun run build`
- `cd frontend && bun run test`
- Execute and record every E2E case in `e2e-api-tests.md` against an isolated
  database.

## Risk And Rollback Points

- Verify the direct-write gate cannot be reached through any inventory service
  caller except the correction executor.
- Verify `updated_at` is serialized without losing timezone or microsecond
  precision before accepting it as the concurrency token.
- Simulate worker loss before and after the apply transaction; neither path may
  create a duplicate ledger effect or an automatic retry.
- Before enabling routes, run an empty-table migration downgrade/re-upgrade.
  After correction history exists, use only forward migration or restore.
