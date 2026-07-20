# Adopt BIGINT identity primary key policy

## Goal

Make the forward-looking PostgreSQL primary-key policy explicit and internally
consistent: new independent business entities use database-generated BIGINT
identity primary keys while existing UUID tables and API contracts remain
unchanged.

## Confirmed Facts

- The repository runs PostgreSQL with SQLModel, Alembic, FastAPI, and a
  generated TypeScript OpenAPI client.
- Existing `user`, `item`, inventory, and AI tables use UUID primary keys.
- `docs/rules/数据库规则.md` already prefers BIGINT identity for new tables, but
  `.trellis/spec/backend/database-guidelines.md` and `type-safety.md` still
  describe UUID as the universal durable-identifier rule.
- PostgreSQL `BIGINT` is a signed 64-bit type; `BIGINT(20)` and an unsigned
  `2^64 - 1` range are not PostgreSQL concepts.

## Requirements

1. Keep every existing UUID primary key, UUID foreign key, API payload, and
   migration unchanged.
2. Define new independent entity, document, ledger, and independently
   referenced line-table primary keys as `BIGINT GENERATED ALWAYS AS IDENTITY`.
3. Permit a new BIGINT-keyed table to reference an existing UUID-keyed table;
   its foreign-key column must match the referenced UUID column.
4. Use a separate business identifier when a domain needs a human-readable
   number. It must not replace the technical primary key.
5. Define exceptions for UUID primary keys: cross-system/offline merge,
   externally opaque identifiers, and shared-primary-key one-to-one extensions.
   Each exception needs a written design rationale.
6. Define API behavior for new numeric IDs: create/update payloads reject
   client-supplied `id` with 422; unauthorized existing resources return 403;
   absent or deleted resources return 404; each module declares its access
   domain.
7. Record the accepted limitation that numeric API IDs continue as JSON
   numbers. Alert only when a table reaches `2^53 - 1`; no automatic block or
   string conversion is introduced.
8. Add document-level migration/model/API test requirements for future modules
   without adding a database table, migration, or runtime code in this task.

## Acceptance Criteria

- [ ] Root terminology distinguishes technical primary key, business
      identifier, and resource access domain.
- [ ] An ADR records the durable BIGINT-default decision and UUID compatibility
      boundary.
- [ ] `docs/rules/数据库规则.md` and Trellis backend specs give the same new-table
      policy and no longer require a new table's own primary key to become UUID
      merely because it references UUID data.
- [ ] The policy uses PostgreSQL `BIGINT`, not `BIGINT(20)`, and documents the
      signed `2^63 - 1` identity maximum plus the accepted JavaScript precision
      risk at `2^53 - 1`.
- [ ] The policy defines the entity/line/association-table distinctions,
      database-generated IDs, API error behavior, and test expectations.
- [ ] No files under `backend/app/**`, frontend source, Alembic migrations, or
      generated client output change.

## Out Of Scope

- Migrating existing UUID keys or creating UUID-to-BIGINT mappings.
- Adding a new business table, reusable ORM mixin, global AST lint rule, or
  database migration.
- Preventing writes after the JavaScript safe-integer alert threshold.
