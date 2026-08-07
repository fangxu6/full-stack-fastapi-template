# Item Service Owns Transactions

## Status

Deprecated; superseded by [ADR-0006](./0006-use-request-scoped-unit-of-work-for-http-writes.md).

## Context

At the time this decision was made, the `items` CRUD flow needed one explicit
transaction owner while the broader HTTP write boundary was still evolving.

## Decision

The `items` CRUD flow makes `services/item.py` responsible for commit and refresh while `crud/item.py` performs database operations without committing. This keeps simple CRUD lightweight while preserving a clear transaction owner.

## Consequences

- Item route handlers call service-level operations.
- Item CRUD callers must explicitly commit or use the item service.
- This transaction contract applies only to items until later tasks migrate users/auth or other modules.

## Related Decisions

- [ADR-0006: Use Request-Scoped Unit Of Work For HTTP Writes](./0006-use-request-scoped-unit-of-work-for-http-writes.md) (superseding decision)
