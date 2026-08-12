# Enterprise Platform Capability Deferred Iterations

## Purpose

This register preserves the independently valuable platform capabilities that
are intentionally outside the parent backlog task's current delivery scope.
It makes the sequencing explicit without treating a backlog item as approved
implementation.

## Traceability Rules

- Deferred items do not fail this parent task's acceptance criteria.
- Each item requires an independent Trellis child task before implementation.
- A dependent item cannot start until its listed prerequisite is complete or
  the child task documents an approved replacement approach.
- MCP is explicitly excluded from the current backlog. Do not add an MCP
  server, transport, dependencies, or tool-exposure work unless a future
  product decision creates a new independently approved Trellis task.

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Authorization foundation | Later capabilities need a uniform actor, role, permission, resource, and action contract. | None | RBAC PRD/design, data migration, frontend/backend enforcement, tests, rollback. |
| D-002 | Structured observability foundation | Existing correlation/error logs do not form an operationally searchable or governable record. | D-001 for actor/action semantics | Log schema, redaction/retention policy, sink/search/alert design, instrumentation, tests. |
| D-003 | Semantic change audit | High-value permission changes need durable, reusable evidence. | D-001, D-002 | Event model/migration, same-transaction writer, retention controls, tests. |
| D-004 | Managed scheduled jobs | Recurring business work requires durable execution, idempotency, retry, and audit behavior. | D-001, D-002, D-003 | Job model, runner choice, operational controls, tests, rollback/runbook. |
| D-005 | External API boundary | The system has no current need for a managed external-consumer API. ADR-0011 explicitly defers it; its completed planning artifacts are archived for future restoration. | D-001, D-002, D-003 | Restore and revalidate the archived plan, then provide consumer identity/scopes, rate limits/quotas, versioning, docs, audit, and contract tests only when the need is approved. |
| D-007 | Business workflow platform | A generic workflow runtime should be driven by a real cross-role process, not framework speculation. | D-001, D-003, D-004 | First-process PRD, state machine, assignments/approvals, timeout/retry, work-item UI/API, tests. |
| D-008 | Alert rule and notification delivery | D-002 defines only a channel-neutral alerting contract; no owned business signal has selected thresholds, recipients, escalation, retry, or delivery channel. | D-002 plus a concrete alert and approved response policy | Rule model, selected email/WeCom/Feishu/DingTalk/in-app adapter, delivery/retry semantics, tests, operations runbook. |
| D-009 | External logging-platform operations | D-002 emits exporter-ready JSON but does not operate a collector, search, dashboard, reader access, or retention enforcement. | D-002 plus an operations-owned platform choice | Collector/export configuration, authorized reader access, 30-day production/14-day staging retention, dashboards, and runbooks. |

## Planning Child Status

- D-003, D-007, D-008, and D-009 have linked planning children. Their current
  PRDs record confirmed constraints and the product decisions required before
  activation; none authorizes implementation.
- D-005's planning child is archived under ADR-0011 because the system does
  not currently need this external API. Restore the archived task and
  revalidate its plan only when a concrete consumer need is approved.
- D-004 is represented by the completed scheduled-task-management delivery.
  Its remaining parent-level dependency reconciliation waits for D-003 rather
  than creating a duplicate scheduler implementation task.

## Suggested Iteration Order

1. D-001 Authorization foundation
2. D-002 Structured observability foundation
3. D-003 Semantic change audit
4. D-004 Managed scheduled jobs
5. D-005 External API boundary
6. D-007 Business workflow platform
7. D-008 Alert rule and notification delivery, once a concrete alert owner and
   response policy exist
8. D-009 External logging-platform operations, once operations selects the
   platform; it may be scheduled independently because it changes no
   application behavior

The only strict ordering is the declared dependency graph. Items at different
branches may be reconsidered together only when their child-task plans prove
the shared contracts and validation scope are compatible.

## Carry-Forward Acceptance Notes

- D-001 must select the first business roles and protected resources before a
  generic permission matrix is implemented.
- D-002 and D-003 must explicitly define PII/secrets redaction, retention,
  who may read audit data, and whether failed authorization is audited.
- D-004 must name at least one recurring business job before choosing a queue
  or scheduler.
- Before D-005 is restored, the product owner must name the first external
  consumer and contractual API use case, then revalidate the archived plan
  against current code and operations under ADR-0011.
- D-007 must name the first cross-role business process and its acceptance
  conditions before selecting a workflow model or engine.
- D-008 must name an important-business or timeout signal, an accountable
  recipient, escalation, and response policy before choosing a delivery adapter.
- D-009 must enforce the D-002 JSON/retention/reader-access contract and test
  the Nginx request-ID overwrite/response-header behavior before production use.

## Remaining Work In Current Scope

The parent task is complete as a planning backlog once its documents are
reviewed. It has no implementation work, deployment change, or child task to
start in the current iteration.
