# Design: BIGINT identity primary key policy

## Boundaries

This is a documentation and durable-decision change. The policy is forward
only: current UUID models are a compatibility baseline, not an implementation
target.

## Policy Contract

| Table shape | Primary-key rule |
| --- | --- |
| Independent entity, document, ledger, or referenced line | `BIGINT GENERATED ALWAYS AS IDENTITY` |
| Pure association with no independent lifecycle | Composite primary key made from its foreign keys |
| One-to-one extension sharing an existing UUID parent's identity | Parent UUID foreign key also serves as the primary key |
| Cross-system/offline or externally opaque identifier | UUID exception with design rationale |

- Each table owns its own identity sequence; IDs are immutable, non-reusable,
  and may contain gaps.
- Foreign-key columns use the type of their referenced target. A BIGINT entity
  may therefore contain UUID audit, owner, or parent references.
- Business identifiers are domain-owned human-readable values. Their generation
  and uniqueness scope are not prescribed by the primary-key policy.
- PostgreSQL uses signed `BIGINT` and the generated positive identity sequence
  cannot exceed `2^63 - 1`. `BIGINT(20)` is not valid PostgreSQL policy.

## API and Authorization Contract

- New public schemas use a numeric `id` response field and never expose it as
  writable input. Create/update models reject an extra `id` field with 422.
- The service owns authorization after lookup: an existing unauthorized resource
  returns 403, while a missing or deleted resource returns 404.
- Every module design declares whether resources are internal-global,
  owner-scoped, unit-scoped, or administrator-scoped.
- Numeric IDs remain JSON numbers. At `MAX(id) >= 9,007,199,254,740,991`, the
  operations signal is alert-only. The user explicitly accepts potential client
  precision loss beyond that value.

## Documentation Architecture

- `CONTEXT.md` owns domain terms only.
- ADR-0004 owns the hard-to-reverse default and why it differs from the UUID
  baseline.
- `docs/rules/数据库规则.md` and `.trellis/spec/backend/*` own implementation
  guidance and future-module tests.
- Existing private knowledge files remain historical descriptions of UUID
  models; they are not rewritten as forward policy.

## Rollback

Revert the documentation and ADR changes together. No runtime data, schema, or
client contract exists to roll back.
