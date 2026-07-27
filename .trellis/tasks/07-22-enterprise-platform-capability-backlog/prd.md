# Enterprise Platform Capability Backlog

## Goal

Maintain a parent planning backlog for progressively completing the platform
capabilities expected of an enterprise operations system. This task does not
implement a capability or create child tasks yet; later work will create,
plan, review, and complete one independently verifiable child task at a time.

## Current Capability Matrix

| Capability | Current State | Assessment |
| --- | --- | --- |
| Logging | `request_id`, unhandled-exception logging, and Sentry initialization exist. | Partially available: unified request and operation logs, search/retention, and alerting are absent. |
| Page authorization | Login and administrator guards plus menu hiding exist; backend checks rely on `is_superuser` and resource ownership. | Partially available: a role-permission-resource model and granular page/button/API authorization are absent. |
| Page-access audit | There is no page-access event store, collection middleware, or query UI; the `audit` module is a skeleton. | Missing. |
| External API | Versioned FastAPI REST endpoints and an OpenAPI schema exist, primarily for the SPA. | Partially available: consumer API key/OAuth client identity, scopes, rate limits, quotas, call auditing, and developer documentation are absent. |
| MCP tools | Retired by ADR-0008; the former AI sidecar and its internal tools are not a current platform capability. | Missing: no current MCP server capability exists. |
| Scheduled jobs | No scheduler/worker dependency, task registration, or runtime entry point is present. | Missing. |
| Business workflow | Retired by ADR-0008; the former AI inventory-query workflow is not a current platform capability. | Missing: there is no general approval, state-transition, work-item, timeout, or retry workflow capability. |

## Requirements

1. Keep this parent task in `planning` state. Do not start implementation,
   create child tasks, or change application behavior as part of this task.
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
structured observability, page-access and operation audit, managed scheduled
jobs, external API boundary, MCP tool gateway, and business workflow platform.

## Acceptance Criteria

- [x] A parent Trellis task exists for this capability backlog and remains in
  `planning` state.
- [x] The current platform baseline and capability gaps are recorded without
  describing the retired AI capability as an active MCP or workflow system.
- [x] Future child tasks have a strict, dependency-aware order with a stated
  rationale for each dependency.
- [x] The parent explicitly defers child-task creation and implementation.
- [ ] Before a child is created, its product owner provides the first concrete
  business use case and acceptance criteria for that capability.

## Out of Scope

- Implementing RBAC, auditing, scheduler infrastructure, public API access,
  MCP transport, or a workflow engine in this parent task.
- Exposing raw database, file-system, shell, network, or private service
  capabilities to external API or MCP consumers.
- Requiring Docker for development, scheduling, or release deployment.
