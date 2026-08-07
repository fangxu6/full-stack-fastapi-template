# Architecture Decision Records

This directory contains the repository's architecture decisions. Status is
explicit on every ADR. Historical records remain linked so a later decision
can be traced without rewriting the original reasoning.

## Status Navigation

### Accepted

- [ADR-0001: Use Ant Design for Complex Admin Components](./0001-use-ant-design-for-complex-admin-components.md)
- [ADR-0002: Evolve Backend as a Modular Monolith](./0002-evolve-backend-as-modular-monolith.md)
- [ADR-0004: Use BIGINT Identity for New Entity Primary Keys](./0004-use-bigint-identity-for-new-entity-primary-keys.md)
- [ADR-0005: Use Celery And Redis For Background Runtime](./0005-use-celery-redis-for-background-runtime.md)
- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md)
- [ADR-0007: Require An Explicit Audit Actor](./0007-require-an-explicit-audit-actor.md)
- [ADR-0008: Remove The AI Inventory Query Capability](./0008-remove-ai-inventory-query-capability.md)
- [ADR-0009: Use A Generic Email Outbox For Non-Report Mail](./0009-use-generic-email-outbox-for-non-report-mail.md)
- [ADR-0010: Use Safe Celery Task Observability Context](./0010-use-safe-celery-task-observability-context.md)
- [ADR-0013: Restrict Detailed Celery Task-Failure Logging](./0013-restrict-detailed-celery-task-failure-logging.md)
- [ADR-0012: Concentrate Scheduler Run Lifecycle State](./0012-concentrate-scheduler-run-lifecycle-state.md)

### Deferred

- [ADR-0011: Defer The External ERP Consumer API Boundary](./0011-defer-external-erp-consumer-api-boundary.md)

### Historical Lifecycle

- [ADR-0003: Item Service Owns Transactions](./0003-item-service-owns-transactions.md) - deprecated; superseded by [ADR-0006](./0006-use-request-scoped-unit-of-work-for-http-writes.md)

## Complete Index

| ADR | Status | Supersedes / Superseded By |
| --- | --- | --- |
| 0001 | Accepted | - |
| 0002 | Accepted | - |
| 0003 | Deprecated | Superseded by 0006 |
| 0004 | Accepted | - |
| 0005 | Accepted | - |
| 0006 | Accepted | Supersedes 0003 |
| 0007 | Accepted | - |
| 0008 | Accepted | - |
| 0009 | Accepted | - |
| 0010 | Accepted | Exception-detail prohibition superseded by 0013 |
| 0011 | Deferred | - |
| 0012 | Accepted | - |
| 0013 | Accepted | Supersedes 0010 exception-detail prohibition |
