# SchedulerRun Terminal Ownership Design

## Seam and Contract

`run_lifecycle.finish_outcome()` remains the single lifecycle seam for terminal
state. Its interface gains the execution lease captured by the caller:

```python
finish_outcome(
    *,
    session: Session,
    run_id: int,
    expected_lease_expires_at: datetime,
    outcome: SchedulerRunOutcome,
    finished_at: datetime | None = None,
) -> SchedulerRun | None
```

`None` means no current claim owns the result. It is not an execution error and
must produce no persistence or alert side effect.

## Data Flow

1. `execute_run()` claims the run, captures its non-null `lease_expires_at`,
   copies immutable execution inputs, and commits before executing the task.
2. The Worker executes outside the transaction, preserving current at-least-once
   behavior.
3. `finish_outcome()` re-reads the run with `FOR UPDATE` and accepts the
   outcome only if the row is `RUNNING` and its lease exactly equals the
   captured lease. It then writes the terminal fields and clears the lease.
4. `execute_run()` performs alert cleanup or failure notification only when the
   lifecycle call accepted the outcome.

An expired lease is a fencing token for a specific claim. A later reclaim
replaces it, so an older Worker cannot write after the new claim has committed.
No new token or database field is required.

## Compatibility and Failure Semantics

- Only the internal orchestration caller and direct lifecycle tests invoke
  `finish_outcome()`, so the required lease parameter has no HTTP or Celery
  compatibility impact.
- A Worker may still finish after its lease expires if no later claim has
  replaced the lease; this preserves the repository's existing lease-reclaim
  semantics. Once reclaimed or terminal, its result is rejected.
- If two results race, the row lock serializes them. The first valid current
  claim commits; the other sees a terminal state or different lease and is a
  no-op.
- Rollback is a code-only revert. No stored data needs transformation.

## Verification Design

Use independent sessions to create the reclaim sequence: capture Worker A's
lease, reclaim after expiry as Worker B, finish B, then submit A's success and
failure. Assert B's terminal fields remain unchanged. Exercise the same stale
failure through `execute_run()` with mocked task execution and assert no alert
is emitted.
