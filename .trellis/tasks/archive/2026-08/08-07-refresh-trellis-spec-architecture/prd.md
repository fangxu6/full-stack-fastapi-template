# Refresh Trellis Specs From Current Architecture

## Goal

Coordinate three independently verifiable child tasks that restore
`.trellis/spec/**` as accurate, concise, source-backed guidance for the current
hybrid FastAPI and React application. The parent owns the audit evidence, task
map, and final integration review; it does not directly edit active
specification rules.

## Background

The specification tree is structurally healthy, but several active rules still
describe the July template-era architecture. The complete findings and source
anchors are in [research/spec-audit-findings.md](research/spec-audit-findings.md).

## Requirements

### R1. Maintain the child-task map

| Finding set | Child task | Priority | Delivery boundary |
| --- | --- | --- | --- |
| F-001 backend hybrid architecture | [08-07-correct-backend-hybrid-architecture-spec](../08-07-correct-backend-hybrid-architecture-spec/prd.md) | P1 | Current module-boundary guidance; simple CRUD remains lightweight. |
| F-002 scheduler lifecycle | [08-07-correct-scheduler-lifecycle-spec](../08-07-correct-scheduler-lifecycle-spec/prd.md) | P1 | Current scheduler registration, orchestration, outcome, lifecycle, and alert ownership. |
| F-003 through F-006 remaining findings | [08-07-refresh-frontend-and-guide-spec-contracts](../08-07-refresh-frontend-and-guide-spec-contracts/prd.md) | P2/P3 | Frontend access, guide accuracy, feature boundaries, and spec governance. |

Each child owns its detailed finding anchors, scope, acceptance criteria, and
implementation planning. All remain in `planning` until individually reviewed
and explicitly approved for activation.

### R2. Preserve scope and verified rules

- The child tasks change only `.trellis/spec/**` and task planning artifacts;
  product source remains read-only evidence.
- Preserve the request Unit of Work, audit actor, cache invalidation,
  structured logging, Celery idempotency/outbox, generated-client, pagination,
  and thin-route contracts that the audit found correct.
- The remaining-findings child must consume the corrected F-002 ownership
  contract before reorganizing async guidance, so it cannot reintroduce stale
  scheduler wording.

## Scope

In scope:

- Parent planning artifacts, the audit evidence register, child-task map, and
  final integration review.

Out of scope:

- Direct edits to `.trellis/spec/**`; implementation belongs to the linked
  child task that owns the relevant finding set.
- Product-source changes under `backend/app/**` or `frontend/src/**`, API,
  database schema, generated client, dependency, migration, or runtime
  configuration changes.
- A generic Clean Architecture rewrite, mandatory module migration, global
  state-management redesign, or rewriting historical records merely to make
  current guidance shorter.

## Acceptance Criteria

- [x] Three planning-state child tasks exist, are linked to this parent, and
      separately own F-001, F-002, and F-003 through F-006.
- [x] Each child records its complete source-backed findings, scope, explicit
      product-source exclusions, and testable acceptance criteria.
- [x] Every P1, P2, and P3 finding in the evidence register has a completed
      child-task correction and no active contradiction remains.
- [x] Cross-child integration confirms the hybrid backend, scheduler
      lifecycle, frontend permission, feature-boundary, and governance
      contracts are mutually consistent.
- [x] Child and final integration validation passes `spec_wiki.py lint`,
      relevant stale-term searches, path-scoped task validation, and
      `git diff --check`.
- [x] The Trellis catalog and maintenance log describe the final spec tree.

## Decisions And Constraints

- This is a documentation-maintenance task tree, not authorization for
  source-code refactoring. A later task may relocate the domain-neutral
  pagination helper.
- Preserve the user-approved simple-CRUD rule. Operational modules do not make
  modularization mandatory for every feature.
- Use current source and focused tests as authority. Historical task prose and
  template wording are supporting evidence only.
- No API E2E plan is required because this task tree changes no API behavior.

## Open Questions

None. The audit evidence resolves the technical scope. Each child needs its
own final planning review before activation.
