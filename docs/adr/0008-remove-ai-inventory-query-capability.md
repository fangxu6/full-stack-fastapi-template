# Remove The AI Inventory Query Capability

Remove the AI inventory query capability in full: the FastAPI BFF and internal endpoints, the sidecar workspace and Compose service, AI configuration and operational documents, generated frontend API surface, and the `ai_run`/`ai_tool_call` persistence model. The capability has no replacement in this delivery, so retaining its public API, secrets, or audit tables would create unsupported operational surface.

## Consequences

- The dashboard no longer presents an AI inventory query workflow, and clients receive no AI inventory endpoints in OpenAPI.
- The removal deletes the sidecar source, FastAPI routers and services, frontend routes, configuration, Compose/deployment references, tests, and operational documentation; it leaves no compatibility route, feature flag, or dormant secret.
- The removal migration destructively deletes AI run and tool-call history; no archive or backup prerequisite is required for this retired capability.
- Downgrade recreates the retired tables and enums as empty schema only; it never restores deleted AI history.
- A future AI capability starts as a new approved design rather than inheriting this sidecar's trust or data model.
