# Workflow Capability YAGNI Audit And Abstraction Triggers

## Goal

D-007 audits existing workflow-like capabilities and records the evidence
required before introducing any shared abstraction. Inventory correction is the
first sample, not a reason to build a workflow platform.

## Confirmed Evidence

- The prerequisite child is archived at
  `08-04-inventory-exception-correction` and records its implementation,
  migration/rollback, focused tests, and process-level validation limits.
- Inventory correction has three domain-owned lifecycles:
  `PENDING_REVIEW -> APPROVED | REJECTED | WITHDRAWN | STALE`, then
  `APPROVED -> APPLIED | APPLICATION_FAILED`; its work item moves
  `APPROVED_PENDING_APPLY -> RUNNING -> SUCCEEDED | TERMINAL_FAILED`; and a
  terminal work item may append one recovery attempt.
- Request, review, and recovery are separate permissioned actions. Self-review
  is allowed, and backend authorization remains authoritative.
- Approval creates one durable work item and initial attempt. A fixed
  scheduler task claims pre-created attempts, applies the inventory/ledger
  change as the System Actor, and treats Celery delivery as at-least-once.
- Stale timestamps, negative-balance validation, lease loss, and duplicate
  delivery have explicit terminal or no-op behavior. Audit summaries are
  allowlisted and raw proposal/reason/exception text is excluded.
- No second business handler or external side-effect workflow exists today.

## Requirements

1. Record the completed inventory process as the audit baseline:
   trigger, roles, actions, state transitions, work-item/attempt lifecycle,
   timing, terminal outcomes, recovery, audit, and UI/API boundaries.
2. Separate reusable vocabulary from inventory-specific behavior. Candidate
   vocabulary may include actor/action decisions, durable work items, attempts,
   leases, terminal outcomes, recovery, and audit evidence; target proposal
   shape, ledger application, handler value, and inventory failure categories
   remain domain-owned.
3. Do not choose a workflow library, global transition registry, reusable
   workflow tables, assignment model, notification engine, timeout policy, or
   generic UI while inventory correction is the only handler.
4. Consider a shared abstraction only after a second concrete workflow or external
   side-effect contract proves the same boundary, concurrency semantics,
   persistence needs, and operator/user expectations. The promotion task must
   compare both workflows and include migration, rollback, API, UI, and test
   contracts.
5. Preserve D-001 authorization, D-003 semantic audit, and D-004 scheduler
   ownership. A future workflow runtime must not replace domain-local state
   matrices or move scheduler lifecycle ownership into business handlers.

## Acceptance Criteria

- [x] The archived inventory correction child is linked as completed evidence;
  its product contract, implementation evidence, migration/rollback outcome,
  and validation limits are captured in `research/`.
- [x] The PRD records inventory states, role actions, exceptions, timing,
  audit, and domain-specific versus reusable boundaries.
- [x] `design.md` defines the promotion gate, ownership boundaries, data-flow
  contract, compatibility, and rollback posture without selecting a runtime.
- [x] `implement.md` defines the future execution checklist, migration/
  rollback plan, and validation gates; it does not authorize product changes
  in this planning task.
- [x] `e2e-api-tests.md` defines the current inventory evidence cases and the
  comparison cases required before any second workflow is generalized.
- [x] The final planning summary is reviewed; no implementation begins from
  this PRD alone.

## Out Of Scope

- Generic workflow or approval engine, transition registry, shared workflow
  schema, assignment/notification/timeout/retry runtime, or workflow designer.
- Product source, database schema, migration, generated client, API, UI, or
  deployment changes in this planning task.
- Rewriting the completed inventory correction process merely to make it look
  generic.

## Deferred Promotion Trigger

Create a separate implementation task only when a second concrete workflow is
approved, its states and side effects are source-backed, and a Ponytail review
shows that sharing a lifecycle mechanism reduces duplication without erasing
domain authorization, transaction, lease, audit, or failure semantics.

## Decision

已评估，因缺乏第二消费者而延期。D-007 不启动实现；库存纠错继续保留
领域内的工作项、执行尝试、租约、幂等和审计语义。未来出现第二个真实
流程时，重新建立独立的比较和实现任务。
