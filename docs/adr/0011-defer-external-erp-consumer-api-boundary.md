# Defer The External ERP Consumer API Boundary

## Status

Deferred. No implementation is approved.

## Context

D-005 planned a managed machine-to-machine API for an ERP/planning system to
read structured inventory balances and inventory documents. The planning task
defined an isolated `/api/external/v1` contract, OAuth2 Client Credentials,
client scopes and credential revocation, Redis-backed rate limits, paginated
materialized snapshots, and a minimal 90-day external-call audit trail.

The system has no current business need for this external integration. Building
the design now would create an unsupported security, credential, rate-limit,
snapshot, and operational-support surface before it has an active consumer.

## Decision

- Do not implement D-005 or change application behavior for this capability.
- Archive the planning task `08-03-external-consumer-api-boundary`; retain its
  PRD, design, implementation plan, and E2E test plan as the starting point
  for a future restoration.
- Do not add external routes, OAuth client/credential models, rate limiting,
  materialized snapshots, external-call audit tables, secrets/configuration,
  migrations, developer documentation, or management UI/API at this time.
- Preserve the existing SPA `/api/v1` authentication, authorization, OpenAPI,
  and generated-client boundary unchanged.

## Consequences

- ERP and planning systems have no supported machine-to-machine read API in
  the current product.
- No deployment, credential issuance, new operational ownership, data
  retention obligation, or integration support commitment is created.
- When a concrete need returns, restore
  `08-03-external-consumer-api-boundary` from the Trellis archive before
  proceeding. Revalidate its plan against the then-current codebase and
  operations, assign named owners and support channels, and obtain explicit
  implementation approval before starting development. The archived design is
  historical planning input, not a standing authorization to implement.
