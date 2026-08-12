# Design: Workflow Capability YAGNI Audit

## Boundary

D-007 is an audit and decision-boundary task. The completed inventory
correction flow remains the executable source of truth; no shared runtime is
introduced until a second workflow demonstrates a repeated boundary.

## Current Evidence Flow

```text
permissioned request -> immutable domain proposal -> review decision
  -> durable work item + attempt -> scheduler claim/lease
  -> domain-owned transaction -> success or terminal failure
  -> audit evidence and optional explicit recovery attempt
```

Inventory owns the proposal, target timestamp/hash, ledger mutation, handler
value, correction statuses, failure categories, and correction UI. The
scheduler owns registration, orchestration, execution outcome, lifecycle
persistence, and alert/outbox handling. Audit owns semantic event persistence.

## Domain-Local Matrices

The inventory request, work-item, and attempt matrices remain in the inventory
contract. A future shared component may provide mechanics, but it must not
merge unrelated state values or replace the owning domain's matrices.

| Candidate repeated concept | Reusable only if a second workflow proves it | Must remain domain-owned |
| --- | --- | --- |
| actor/action decision | permissioned command and reviewer attribution have the same contract | permission names and business authorization |
| work item / attempt | durable one-opportunity boundary and idempotent claim semantics repeat | target payload, handler, and domain state |
| lease / terminal outcome | stale worker and lease-loss behavior can be expressed identically | failure categories and compensation |
| audit evidence | action code, allowlist, retention, and reader policy align | summary keys and business meaning |
| timing | both workflows use the same scheduler ownership and retry policy | task cadence and no-backfill policy |

Do not create `ALL_TRANSITIONS`, a global callback registry, or a status table
just because both workflows have states. The state-transition spec requires
aggregate-local matrices, concrete locks/tokens, and explicit idempotency.

## Promotion Gate

A second workflow must provide:

1. a real cross-role trigger and named actors;
2. at least one state transition with a distinct side effect;
3. durable work/attempt or an explicitly justified alternative;
4. concurrency, lease, retry, terminal, and recovery semantics;
5. audit and redaction requirements; and
6. API/UI or operator contracts that can be compared with inventory.

The promotion design must show which fields and transitions are common,
which remain domain extensions, and why a shared mechanism is smaller and
safer than two local implementations. Absence of a second handler is a reason
to defer, not a reason to add placeholders.

## Compatibility, Migration, And Rollback

This task has no runtime or schema migration. Existing inventory tables,
permissions, scheduler tasks, audit events, generated client, and UI remain
unchanged. Rollback is documentation-only: remove or revise the planning
artifacts without data repair. Any future shared runtime requires a separate
task with additive migration, dual-read/write or backfill analysis, downgrade
limits, and a tested rollback point before moving a domain off its local path.

## Risks

- Premature abstraction can erase inventory's proposal and ledger invariants.
- A shared retry policy can accidentally turn terminal correction failures into
  automatic reapplication.
- A generic UI can expose queues or actions without the domain permission
  matrix.
- Treating scheduler delivery as business application would reintroduce
  duplicate side effects.
