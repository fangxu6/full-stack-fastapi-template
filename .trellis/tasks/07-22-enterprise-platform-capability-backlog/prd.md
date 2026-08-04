# Enterprise Platform Capability Backlog

## Goal

Maintain a parent planning backlog for progressively completing the platform
capabilities expected of an enterprise operations system. This task does not
implement a capability. It may create planning-state child tasks, but no child
may enter implementation until its product use case, acceptance criteria, and
required planning artifacts are reviewed.

## Current Capability Matrix

| Capability | Current State | Assessment |
| --- | --- | --- |
| Logging | `request_id`, unhandled-exception logging, and Sentry initialization exist. | Partially available: unified request and operation logs, search/retention, and alerting are absent. |
| Page authorization | Login and administrator guards plus menu hiding exist; backend checks rely on `is_superuser` and resource ownership. | Partially available: a role-permission-resource model and granular page/button/API authorization are absent. |
| Semantic change audit | There is no reusable semantic-change event store; the `audit` module is a skeleton. | Missing. |
| External API | Versioned FastAPI REST endpoints and an OpenAPI schema exist, primarily for the SPA. | Partially available: consumer API key/OAuth client identity, scopes, rate limits, quotas, call auditing, and developer documentation are absent. |
| MCP tools | Explicitly excluded from the current backlog; the former AI sidecar and its internal tools are retired. | No MCP server capability is planned. Reintroduction requires a future product decision and a new independently approved Trellis task. |
| Scheduled jobs | No scheduler/worker dependency, task registration, or runtime entry point is present. | Missing. |
| Business workflow | Retired by ADR-0008; the former AI inventory-query workflow is not a current platform capability. | Missing: there is no general approval, state-transition, work-item, timeout, or retry workflow capability. |

## Requirements

1. Keep this parent task in `planning` state. Do not start implementation or
   change application behavior as part of this task. Planning-state child tasks
   may be created to record and refine a deferred capability.
2. Record a dependency-aware, strict priority order for future child tasks.
   Each child must be independently planned with its own PRD, design,
   implementation plan, migration/rollback plan, and validation scope before
   it begins.
3. Preserve current FastAPI, React, PostgreSQL, and generated OpenAPI-client
   boundaries. Deployment work must not introduce Docker as
   a required runtime assumption.
4. Treat audit data, credentials, API tokens, and future tool inputs as sensitive:
   each implementing child must define data minimization, retention, access,
   and redaction rules before storing or exposing them.
5. Keep the deferred deliverables and their dependencies in
   [deferred-iterations.md](deferred-iterations.md). Promotion of an item to
   implementation requires a separate child task.

## Ordered Future Child Backlog

The dependency-aware order, stable IDs, and future planning gates are defined
in [deferred-iterations.md](deferred-iterations.md): authorization foundation,
structured observability, semantic change audit, managed scheduled
jobs, external API boundary, and business workflow platform.

## Acceptance Criteria

- [x] A parent Trellis task exists for this capability backlog and remains in
  `planning` state.
- [x] The current platform baseline and capability gaps are recorded without
  describing the retired AI capability as an active MCP or workflow system.
- [x] Future child tasks have a strict, dependency-aware order with a stated
  rationale for each dependency.
- [x] The parent defers child implementation; planning children remain in
  `planning` until their scope is approved.
- [x] Planning child tasks exist for D-003, D-007, D-008, and D-009; none has
  started implementation. D-005's completed planning artifacts are archived
  under ADR-0011 and must be restored and revalidated before implementation.
- [ ] Before a planning child enters `in_progress`, its product owner provides
  the first concrete business use case and testable acceptance criteria.

## Out of Scope

- Implementing RBAC, auditing, scheduler infrastructure, public API access,
  MCP transport, or a workflow engine in this parent task.
- Exposing raw database, file-system, shell, network, or private service
  capabilities to external API consumers.
- Requiring Docker for development, scheduling, or release deployment.
