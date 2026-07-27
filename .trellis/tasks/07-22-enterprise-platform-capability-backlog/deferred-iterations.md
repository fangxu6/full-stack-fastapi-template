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

## Deferred Items

| ID | Deferred Scope | Reason | Dependencies | Future Deliverables |
| --- | --- | --- | --- | --- |
| D-001 | Authorization foundation | Later capabilities need a uniform actor, role, permission, resource, and action contract. | None | RBAC PRD/design, data migration, frontend/backend enforcement, tests, rollback. |
| D-002 | Structured observability foundation | Existing correlation/error logs do not form an operationally searchable or governable record. | D-001 for actor/action semantics | Log schema, redaction/retention policy, sink/search/alert design, instrumentation, tests. |
| D-003 | Page-access and operation audit | Page views, denied access, and privileged changes need durable, queryable evidence. | D-001, D-002 | Event model/migration, capture boundary, query API/UI, retention controls, tests. |
| D-004 | Managed scheduled jobs | Recurring business work requires durable execution, idempotency, retry, and audit behavior. | D-001, D-002, D-003 | Job model, runner choice, operational controls, tests, rollback/runbook. |
| D-005 | External API boundary | The SPA API is not yet a managed external-consumer product surface. | D-001, D-002, D-003 | Consumer identity/scopes, rate limits/quotas, versioning, docs, audit, contract tests. |
| D-006 | MCP tool gateway | MCP exposure must reuse approved authorization, audit, and domain boundaries rather than expose private internals. | D-001, D-002, D-003, D-005 | MCP transport/auth design, read-first tool contracts, discovery docs, tests, operations guide. |
| D-007 | Business workflow platform | A generic workflow runtime should be driven by a real cross-role process, not framework speculation. | D-001, D-003, D-004 | First-process PRD, state machine, assignments/approvals, timeout/retry, work-item UI/API, tests. |
| D-008 | Alert rule and notification delivery | D-002 defines only a channel-neutral alerting contract; no owned business signal has selected thresholds, recipients, escalation, retry, or delivery channel. | D-002 plus a concrete alert and approved response policy | Rule model, selected email/WeCom/Feishu/DingTalk/in-app adapter, delivery/retry semantics, tests, operations runbook. |
| D-009 | External logging-platform operations | D-002 emits exporter-ready JSON but does not operate a collector, search, dashboard, reader access, or retention enforcement. | D-002 plus an operations-owned platform choice | Collector/export configuration, authorized reader access, 30-day production/14-day staging retention, dashboards, and runbooks. |

## Suggested Iteration Order

1. D-001 Authorization foundation
2. D-002 Structured observability foundation
3. D-003 Page-access and operation audit
4. D-004 Managed scheduled jobs
5. D-005 External API boundary
6. D-006 MCP tool gateway
7. D-007 Business workflow platform
8. D-008 Alert rule and notification delivery, once a concrete alert owner and
   response policy exist
9. D-009 External logging-platform operations, once operations selects the
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
- D-005 must name the first external consumer and contractual API use case.
- D-006 must choose an MCP transport and client-authentication model; it must
  never expose raw database, shell, file-system, network, or private-service
  access.
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
