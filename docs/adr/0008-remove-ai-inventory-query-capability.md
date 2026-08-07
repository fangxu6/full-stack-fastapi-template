# Remove The AI Inventory Query Capability

## Status

Accepted. The implementation is complete; the retirement is irreversible for
deleted rows and downgrade recreates schema only.

## Context

The AI inventory query capability had a FastAPI BFF and internal endpoints,
sidecar workspace and Compose service, configuration and operational documents,
generated frontend API surface, and `ai_run`/`ai_tool_call` persistence. It has
no replacement in this delivery, so retaining its public API, secrets, or audit
tables would create unsupported operational surface.

## Decision

Remove the capability in full, including its routes, sidecar, configuration,
deployment references, generated client surface, tests, operational
documentation, and persistence model. Keep the original creation migration
immutable and add a forward removal migration. Its downgrade recreates the
retired empty schema only; it never restores historical rows.

Before executing the destructive migration in a production environment, the
data owner must record classification, retention/disposal authority, scope,
and approval. The record must either reference a verified recoverable backup
whose retention covers the decision or explicitly approve that recovery is no
longer available. A schema downgrade is not a substitute for that governance
or for backup/restore.

## Consequences

- The dashboard no longer presents an AI inventory query workflow, and clients
  receive no AI inventory endpoints in OpenAPI.
- The removal deletes the sidecar source, FastAPI routers and services,
  frontend routes, configuration, Compose/deployment references, tests, and
  operational documentation; it leaves no compatibility route, feature flag,
  or dormant secret.
- The removal migration destructively deletes AI run and tool-call history;
  production execution requires the documented disposal decision and backup or
  explicit no-recovery approval described above.
- Downgrade recreates the retired tables and enums as empty schema only; it
  never restores deleted AI history.
- A future AI capability starts as a new approved design rather than inheriting
  this sidecar's trust or data model.

## Related Decisions

- [ADR-0002: Evolve Backend as a Modular Monolith](./0002-evolve-backend-as-modular-monolith.md)
- [ADR-0004: Use BIGINT Identity For New Entity Primary Keys](./0004-use-bigint-identity-for-new-entity-primary-keys.md)
