# External Logging-Platform Operations

## Goal

Turn D-009 into an operations-owned promotion gate: select and approve the
smallest external logging service that can collect the existing safe stdout
NDJSON, provide authorized incident lookup, and enforce the already-decided
retention policy. This planning task does not deploy a logging platform.

## Confirmed Context

- The completed D-002 application boundary emits newline-delimited JSON to
  stdout through `backend/app/core/observability.py`. It is deliberately
  best-effort and has no collector credential, buffer, log database, query
  API, or frontend UI.
- The approved event contract permits only the structured allowlist and keeps
  raw request data, credentials, business identifiers, and ordinary
  application logger records out of the collector stream.
- Production retention is 30 days and staging retention is 14 days. Local
  development has no persistent-log requirement. Log-reader authorization is
  owned by operations and is separate from application RBAC.
- `frontend/nginx.conf` currently serves the SPA only; it does not proxy the
  API. The backend accepts a valid `X-Request-ID` as its direct-access
  fallback. A future public API proxy must generate and overwrite that header,
  then own the response header.

## Requirements

1. Operations names one accountable service owner, on-call/escalation path,
   deployment boundary, and approved platform. The choice may be Loki, ELK,
   a managed cloud log service, or an existing organization platform, but it
   must not create a new application dependency.
2. Before implementation, operations records a short decision sheet proving
   that the selected platform can:
   - collect line-delimited JSON from each deployed backend, worker, and beat
     stdout source without changing application availability;
   - query by `request_id`, time, severity, `event_name`, `environment`,
     `route_template`, status, and dependency while retaining raw JSON for
     incident investigation;
   - restrict read access to an operations-managed group, including an
     auditable break-glass path; application administrators receive no
     implicit access;
   - enforce and demonstrate 30-day production / 14-day staging deletion;
   - provide a minimal incident view for request-ID lookup and error or
     dependency-failure triage; and
   - report collector parse/export failures without making the application
     block, retry, or store logs.
3. The promotion plan defines only the selected platform's collector/export,
   reader provisioning, retention rule, two minimal incident views, and an
   operations runbook. It does not add alert rules, application log readers,
   distributed tracing, log-derived audit records, or a second log pipeline.
4. If a public API reverse proxy is part of the selected deployment, the plan
   includes a proxy integration test: a caller-supplied request ID is
   overwritten, the returned `X-Request-ID` is searchable in collected JSON,
   and the proxy is the sole response-header authority. Otherwise this test
   remains deferred with the proxy rollout.

## Acceptance Criteria

- [ ] Operations has approved the platform, owner, deployment boundary,
  reader group, break-glass policy, and incident escalation path.
- [ ] The platform decision sheet demonstrates every capability in Requirement
  2, including retention evidence for both production and staging.
- [ ] The implementation plan names the exact collector configuration and
  validates collection from every runtime that emits application NDJSON.
- [ ] Authorized operators can perform request-ID lookup and error/dependency
  triage; unauthorized application or platform administrators cannot read
  operational logs by default.
- [ ] Collector/export failure is visible to operations and does not alter
  application requests, tasks, or durable state.
- [ ] A deployed API proxy, when introduced, proves its request-ID overwrite
  and response-header contract end to end.

## Promotion Inputs

This task remains in `planning` until operations supplies all of the following:

- the approved platform and its administrative owner;
- target runtime/deployment topology and the collector's operating owner;
- the authorized reader group and incident/break-glass policy; and
- an implementation environment where retention and access can be tested.

Those are product and operations decisions, not repository questions. Once
they exist, revise this task with the chosen platform and obtain a fresh
implementation approval before `task.py start`.

## Current Decision

Evaluated on 2026-08-12: no usable logging platform or accountable operations
owner currently exists. D-009 is therefore deferred in `planning`; no
collector, platform trial, temporary owner, or application-side substitute is
authorized. Reopen this plan only when the promotion inputs are available.

## Out of Scope

- Selecting a platform on behalf of operations or provisioning one before the
  promotion inputs are approved.
- Application schema, Python dependency, frontend, database, generated-client,
  or application credential changes.
- Alert rules, notification delivery, dashboards beyond the two incident
  views, SLO/APM/tracing, or a log query API/UI.
- Treating operational logs as durable audit evidence.
