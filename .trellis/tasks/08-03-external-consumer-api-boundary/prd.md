# External consumer API boundary

## Goal

D-005: plan a managed API surface for the first approved external consumer.

## Confirmed Context

- The current FastAPI API and OAuth2 password flow serve the SPA, not an
  external-consumer product.
- D-003 must define durable access and privileged-operation audit boundaries
  before this task can safely expose a consumer API.

## Requirements

- Product owner identifies the first external consumer, its contractual use
  case, and the minimum endpoint set.
- Define consumer identity, authentication, scopes, quotas/rate limits,
  versioning, call audit, developer documentation, and revocation behavior.
- Preserve current SPA authentication and generated-client contracts unless a
  reviewed compatibility plan changes them.

## Acceptance Criteria

- [ ] Product owner approves the first consumer and its testable API use case.
- [ ] PRD names identity, scope, quota, audit, versioning, and lifecycle
  requirements for that consumer.
- [ ] Design, implementation plan, compatibility/rollback plan, and contract
  tests are reviewed before `task.py start`.

## Out of Scope

- Exposing a generic public API or modifying the SPA authentication flow before
  an approved consumer contract exists.
