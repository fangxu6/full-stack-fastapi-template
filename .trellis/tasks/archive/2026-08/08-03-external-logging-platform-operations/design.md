# Design: External Logging-Platform Operations

## Decision Boundary

The application boundary is complete: it emits privacy-safe stdout NDJSON and
continues serving traffic when logging cannot be written or collected. D-009
owns only the runtime path after stdout. It must not insert an application
agent, SDK, credential, queue, database, or fallback sink.

```text
backend / worker / beat stdout NDJSON
  -> operations-owned collector
  -> selected operations logging platform
  -> operations-only reader group and retention policy
```

The collector may be host-, container-, or platform-managed. The selected
deployment model must describe every runtime producer; an API-only collector
is incomplete when workers or beat emit production events.

## Minimum Operational Contract

| Concern | Required decision or proof |
| --- | --- |
| Ownership | One named operations owner for platform, collector, access requests, and incident escalation. |
| Availability | Collector outages may lose or delay logs according to the platform policy, but must never block application HTTP, Celery, or persistence. |
| Parsing | One JSON line is one event. Malformed-line rejection/metrics belong to the collector, not an application retry path. |
| Search | Searchable fields include `request_id`, timestamp, severity, `event_name`, `environment`, `route_template`, status, and dependency. |
| Access | Operations-managed group only, auditable break-glass path, no implicit access through application RBAC. |
| Retention | Production deletes after 30 days; staging deletes after 14 days; local is not persisted by this task. |
| Incident views | Request-ID lookup plus error/dependency-failure triage. More dashboards require an owned alert or SLO use case. |
| Data boundary | Preserve D-002's allowlist; do not add sensitive fields or use logs as semantic audit evidence. |

## Request Correlation

There are two valid modes:

1. Direct backend access: the application retains its current validated or
   generated 32-character hexadecimal request ID and response header.
2. Public API proxy: Nginx generates a request ID, overwrites inbound
   `X-Request-ID`, forwards it upstream, hides any upstream duplicate, and
   emits the same value as the response header.

The proxy is not configured by this planning task. When it is deployed, the
integration assertion is deliberately small: send a request with a spoofed
header, take the response header value, and query the platform for exactly the
same `request_id`. This proves overwrite, propagation, collection, and reader
lookup without storing a second correlation record.

## Rollout And Rollback

Roll out the collector to one non-production runtime first, prove parsing,
reader denial/allow behavior, retention configuration, and the two incident
views, then cover the remaining runtime producers before production.

Rollback disables or removes the collector/export configuration and revokes
the new reader group. It does not change application code or data. Retained
records stay subject to the selected platform's approved deletion policy; do
not use rollback to bypass retention or access controls.

## Ponytail Assessment

- Keep: one existing stdout stream, one collector, one platform, one reader
  group, two incident views, and the existing request ID.
- Defer: vendor selection, tracing, metrics, a custom shipper, app-side
  buffering, a log database/API/UI, alerting, and broad dashboard catalogs.
- Promote more only when an operations owner supplies a concrete incident,
  SLO, compliance, or alert-response requirement that the minimum contract
  cannot meet.
