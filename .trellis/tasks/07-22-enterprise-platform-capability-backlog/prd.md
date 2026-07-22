# Enterprise Platform Capability Backlog

## Goal

Maintain a parent planning backlog for progressively completing the platform
capabilities expected of an enterprise operations system. This task does not
implement a capability or create child tasks yet; later work will create,
plan, review, and complete one independently verifiable child task at a time.

## Current Capability Matrix

| Capability | Current State | Assessment |
| --- | --- | --- |
| Logging | `request_id`, unhandled-exception logging, Sentry initialization, and structured AI-query result logs exist. | Partially available: unified request and operation logs, search/retention, and alerting are absent. |
| Page authorization | Login and administrator guards plus menu hiding exist; backend checks rely on `is_superuser` and resource ownership. | Partially available: a role-permission-resource model and granular page/button/API authorization are absent. |
| Page-access audit | There is no page-access event store, collection middleware, or query UI; the `audit` module is a skeleton. | Missing. |
| External API | Versioned FastAPI REST endpoints and an OpenAPI schema exist, primarily for the SPA. | Partially available: consumer API key/OAuth client identity, scopes, rate limits, quotas, call auditing, and developer documentation are absent. |
| MCP tools | The AI sidecar has internal, read-only Mastra tools. | Missing: these tools are not an MCP server. |
| Scheduled jobs | No scheduler/worker dependency, task registration, or runtime entry point is present. | Missing. |
| Business workflow | `createInventoryWorkflow` orchestrates one AI query. | Missing: there is no general approval, state-transition, work-item, timeout, or retry workflow capability. |

## Requirements

1. Keep this parent task in `planning` state. Do not start implementation,
   create child tasks, or change application behavior as part of this task.
2. Record a dependency-aware, strict priority order for future child tasks.
   Each child must be independently planned with its own PRD, design,
   implementation plan, migration/rollback plan, and validation scope before
   it begins.
3. Preserve current FastAPI, React, PostgreSQL, generated OpenAPI-client, and
   private AI-sidecar boundaries. Deployment work must not introduce Docker as
   a required runtime assumption.
4. Treat audit data, credentials, API tokens, and AI tool inputs as sensitive:
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
  overstating the private AI tool implementation as MCP or a generic workflow
  system.
- [x] Future child tasks have a strict, dependency-aware order with a stated
  rationale for each dependency.
- [x] The parent explicitly defers child-task creation and implementation.
- [ ] Before a child is created, its product owner provides the first concrete
  business use case and acceptance criteria for that capability.

## Out of Scope

- Implementing RBAC, auditing, scheduler infrastructure, public API access,
  MCP transport, or a workflow engine in this parent task.
- Exposing raw database, file-system, shell, network, or private sidecar
  capabilities to external API or MCP consumers.
- Requiring Docker for development, scheduling, or release deployment.
