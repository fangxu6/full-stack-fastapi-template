# Evolve Backend as Modular Monolith

## Status

Accepted. This is the current backend placement and decomposition boundary.

## Context

The backend already has valuable FastAPI, SQLModel, shared error handling, and
generated-client infrastructure. Most simple behavior remains on the
`api/routes -> services -> crud -> ORM` path, while bounded capabilities such
as scheduler and email outbox have earned module boundaries.

## Decision

The backend evolves as a modular monolith. Keep simple CRUD on the lightweight
route/service/CRUD path. Add `backend/app/modules/<name>/` only when a domain
earns a boundary through multi-table workflows, state transitions, background
tasks, external-system calls, events, or cross-module collaboration. Do not
rewrite the system around strict ports/adapters or split it into microservices
without a separate approved decision.

## Considered Options

- Keep only the global `api -> services -> crud` layout: lowest short-term churn, but it keeps growing unbounded global files.
- Move gradually to module boundaries only for domains that earn the extra structure: preserves the working stack while avoiding module ceremony for simple CRUD.
- Rewrite around strict use cases and ports/adapters: cleaner on paper, but too much migration risk for the current template-derived backend.
- Split into microservices: creates independent deployable units, but adds deployment, transaction, auth, observability, and data-ownership complexity before the repo has real service boundaries.

## Consequences

- Existing lightweight CRUD remains low ceremony and easy to trace.
- Bounded modules can own richer workflows without creating a second backend
  architecture for every feature.
- A future module must document its boundary and cross-layer contracts; the
  `modules/*` directory is not a generic holding area.

## Related Decisions

- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
