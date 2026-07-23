# Structured Observability Foundation Deferred Iterations

## Purpose

D-002 establishes privacy-safe operational telemetry only. This register keeps
confirmed later work visible without turning it into a D-002 acceptance
criterion.

## Traceability Rules

- Deferred items do not fail the current task's acceptance criteria.
- Each item requires its own Trellis task, reviewed PRD, design,
  implementation plan, migration/rollback plan, and validation scope before
  implementation.
- A promoted item retains the D-002 schema allowlist, request correlation,
  stable source-name registry, and sensitive-data boundary unless a reviewed
  revision explicitly changes them.
- D-003, not operational logs, is the first place that may introduce durable
  identity-traceable activity records or a user-visible query surface.

## Deferred Items

| ID | Deferred scope | Reason | Dependencies | Future deliverables |
| --- | --- | --- | --- | --- |
| D-003 | Page-access and operation audit | D-002 records omit actor identity and business/resource identifiers, so they cannot be durable audit evidence. | Completed D-001 and D-002. | Persistent audit event model, capture boundaries, query API/UI, reader/retention policy, and tests. |
| D-004 | Managed scheduled-job telemetry | No approved scheduler or recurring business job exists. D-002 event conventions are reusable, but job execution semantics are not. | D-001, D-002, D-003, plus a real recurring job. | Job model/runner, execution telemetry, retry controls, audit linkage, tests, and runbook. |
| D-005 | External API telemetry and consumer controls | The API currently serves the SPA rather than external consumers. | D-001, D-002, D-003, plus approved client identity/scopes. | Consumer identity, scopes, quotas/rate limits, public contract telemetry, audit policy, and tests. |
| D-006 | MCP gateway telemetry | The internal AI-sidecar tools are not an MCP product surface. | D-001, D-002, D-003, D-005, plus an approved transport/client model. | MCP request/dependency events, authorization/audit integration, transport tests, and operations guide. |
| D-007 | Business workflow platform | A generic workflow runtime needs a concrete cross-role process first. | D-001, D-003, D-004, plus a first-process PRD. | State machine, assignments/approvals, timeout/retry, work-item UI/API, telemetry, and tests. |
| D-008 | Alert rule and notification delivery | D-002 defines a channel-neutral design only; no business signal has selected thresholds, recipients, escalation, retry, or ownership. | D-002 plus a concrete business/timeout alert and approved response policy. | Rule model, selected email/WeCom/Feishu/DingTalk/in-app adapter, delivery/retry semantics, tests, and operations runbook. |
| D-009 | External collector, search, dashboards, and retention enforcement | D-002 emits exporter-ready JSON only; runtime deployment and log-reader access belong to operations. | D-002 plus an operations-owned platform choice. | Collector configuration, reader access control, 30-day production/14-day staging retention enforcement, dashboards, and runbooks. |

## Suggested Iteration Order

1. D-003 page-access and operation audit.
2. D-004 managed scheduled jobs and D-005 external API boundary, in either
   order only after their concrete use cases are approved.
3. D-006 MCP tool gateway and D-007 business workflow platform after their
   stated dependencies.
4. D-008 alerting when an owned alert scenario exists.
5. D-009 external-platform operational deployment when operations selects the
   logging platform; it may be scheduled independently because it does not
   change application behavior.

## Carry-Forward Acceptance Notes

- A future source name must be registered and tested before a new service or
  startup component emits dependency/startup telemetry.
- No alert can use an application log query endpoint, because D-002 provides
  none.
- A durable audit record must separately decide identity, business identifiers,
  reader access, retention, and redaction; operational records remain
  insufficient.
- An external platform deployment must test the Nginx overwrite/response-header
  request-ID contract and enforce authorized-operations-only reader access.

## Remaining Work In Current Scope

- Complete the reviewed D-002 implementation plan, including application and
  Uvicorn safe NDJSON configuration, Sentry scrubbing, the initial source
  registry, and the E2E cases.
- No deferred row is partially exposed through a placeholder control, endpoint,
  or permissive fallback.
