# Inventory Workflow Handoff Evidence

Source: `.trellis/tasks/archive/2026-08/08-04-inventory-exception-correction/`.

The completed child defines one inventory-only correction flow. It uses an
immutable typed proposal and three domain-local lifecycles: request review and
application, work-item execution, and application attempts. Request/review/
recovery permissions are separate but may be held by one user, so self-review
is allowed. Approval creates one work item and one pending attempt; the fixed
minute scheduler claims that row and the System Actor applies the existing
inventory service in one audited transaction.

The child explicitly excludes generic approval engines, handler registries,
assignment, notifications, timeout reminders, automatic retry, generic work
item UI, and external effects. It records stable stale-target,
negative-balance, execution-lost, and execution-failed outcomes; terminal
failure is recoverable only through a fresh explicit attempt. Its E2E plan
covers direct-write blocking, request/review, atomic application, stale and
negative failures, lease loss, duplicate delivery, recovery, authorization,
redaction, and scheduler batch isolation.

Conclusion: inventory proves a reusable vocabulary and comparison baseline, but
not a generic runtime. A second concrete handler or external side-effect
workflow is required before promoting shared persistence or execution
mechanics.
