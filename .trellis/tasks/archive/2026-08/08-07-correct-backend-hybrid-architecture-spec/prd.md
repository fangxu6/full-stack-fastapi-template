# Correct Backend Hybrid Architecture Spec

## Goal

Make the active backend guidance describe the architecture that engineers use
today: retain the lightweight CRUD path where it fits, and use a module-local
boundary for an operational domain only when its real workflow needs one.

## Background

F-001 is a P1 specification defect. Three active backend documents still
present module boundaries as a future transition, even though production API
routing includes inventory, inventory corrections, IAM, and scheduler module
routers. The full source record is
[research/backend-hybrid-architecture-evidence.md](research/backend-hybrid-architecture-evidence.md).

## Confirmed Facts

- `.trellis/spec/backend/index.md:9-15,61-79` calls the architecture a
  `platform-batch-0 transition`, says most business behavior is service-first,
  and labels `modules/*` future-facing.
- `.trellis/spec/backend/directory-structure.md:9,45-47,69-70` repeats that
  modules are secondary until they become richer.
- `.trellis/spec/backend/quality-guidelines.md:249-261` says `modules/*` is
  not already mature.
- CodeGraph confirms `backend/app/api/main.py:18-23` assembles the lightweight
  items router and the inventory, inventory-correction, IAM, scheduler, and
  generic modules routers in the production API path.
- CodeGraph confirms `backend/app/api/routes/items.py:14-72` remains a thin
  route delegating item operations to `services.item`. Inventory correction,
  IAM, and scheduler routers delegate to module-local collaborators.

## Requirements

1. Revalidate the cited source and active-specification anchors before editing.
   Use CodeGraph first for code understanding; use narrow text searches only
   for specification wording and link checks.
2. Replace the transition and future-module narrative in the three named
   backend documents with a source-backed hybrid architecture contract.
3. Make `backend/directory-structure.md` the canonical owner of backend
   placement guidance. `backend/index.md` and `backend/quality-guidelines.md`
   may summarize it or link to it, but must not restate an incompatible maturity
   model.
4. Preserve two supported placement paths:
   - lightweight CRUD: `api/routes -> services -> crud -> models/schemas`;
   - operational domain: `modules/<domain>/` owns its router and domain-local
     collaborators when bounded-domain complexity makes that boundary useful.
5. Use observable complexity, not a maturity milestone, as the selection
   criterion. Relevant evidence includes multi-table state transitions, durable
   asynchronous work, external integration, events, or collaboration across
   domains.
6. Make the architecture escalation rule explicit without requiring Clean
   Architecture ceremony by default:
   - SQLModel models, service functions, Pydantic schemas, and FastAPI
     `Depends` remain the default entity, use-case, DTO, and DI mechanisms for
     lightweight CRUD.
   - Add a persistence-independent domain entity only when business invariants
     need to be reused outside the ORM model.
   - Promote service orchestration into a module-local application use case
     only for multi-table workflows, state transitions, durable work, or
     cross-domain collaboration; do not add one class per endpoint.
   - Treat schemas as DTOs at HTTP/task/event boundaries and add adapters only
     for external protocol translation or a genuinely replaceable integration.
   - Keep FastAPI request dependencies as `Depends`; use constructor injection
     only for replaceable external clients or complex lifecycles, without a DI
     container or service locator.
7. Preserve unrelated verified contracts: Unit of Work, audit actor, cache
   invalidation, structured logging, Celery reliability, generated-client,
   pagination, and thin routes.

## Key Decisions

- Do not add an architecture guide. The existing directory guide is already
  the first placement read, so making it canonical is the smallest durable
  correction.
- Do not require a module boundary for every new feature. A simple CRUD
  workflow remains intentionally lightweight.
- Do not use router registration alone to classify every `modules/*` directory
  as an API domain. It proves the operational examples above, while individual
  module responsibilities remain source-backed.
- Do not introduce entity mappers, use-case classes, repository interfaces,
  adapters, or a DI container merely to satisfy a named architecture pattern.

## Scope

In scope:

- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/quality-guidelines.md`
- Required specification indexes, links, and maintenance-log entry.
- This task's planning artifacts and parent integration record.

Out of scope:

- Product changes under `backend/app/**` or `frontend/src/**`, generated
  clients, tests, database schema, dependencies, migrations, and runtime
  configuration.
- A repository-wide module migration, a Clean Architecture rewrite, or a
  change to scheduler lifecycle guidance owned by F-002.

## Acceptance Criteria

- [ ] The three active backend documents no longer characterize current
      operational module boundaries as future-facing, a transition, secondary
      until richer, or not mature.
- [ ] `directory-structure.md` is the sole canonical placement contract and
      accurately documents both the lightweight CRUD path and the
      domain-complexity-based module path.
- [ ] `index.md` and `quality-guidelines.md` link to or accurately summarize
      that canonical contract without duplicate implementation signatures.
- [ ] The corrected guidance does not require a module migration and preserves
      the `items` path as a valid lightweight CRUD reference.
- [ ] The canonical placement contract states the default and escalation
      triggers for domain entities, application use cases, DTO/adapters, and
      DI without making any of them mandatory ceremony for simple CRUD.
- [ ] All changed source-backed statements have a current code anchor or an
      explicit source revalidation record.
- [ ] `python .trellis/scripts/spec_wiki.py lint`, path-scoped stale-term
      searches, `python .trellis/scripts/task.py validate <task-dir>`, and
      `git diff --check` pass.

## Risks And Deferred Work

- This task must not normalize every current module directory into a public
  router or infer domain behavior that the source does not show.
- The remaining-findings child owns cross-layer/reuse guidance and spec-size
  governance. This task supplies the stable backend placement contract it can
  link to later.

## Open Questions

None. The source evidence resolves the architecture contract and no
user-owned product decision remains.
