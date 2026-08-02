# Design: PostgreSQL Chinese Comment Backfill

## Boundary

One Alembic revision owns the historical comment backfill. It targets only the
18 `public` tables registered by `app.models`; `alembic_version` and any
unmanaged database objects are excluded.

## Data Flow

The revision stores a table-to-comment mapping, including nested column
comments. `upgrade` applies them with Alembic table/column comment operations.
`downgrade` iterates the same mapping and clears only those comments. PostgreSQL
catalog functions verify the persisted result after each direction.

## Compatibility

`COMMENT ON` changes metadata only. It does not rewrite rows, alter constraints,
or affect FastAPI/OpenAPI. The existing forward-only rule remains the source of
truth for new model objects; no 198-field model rewrite is introduced solely for
this historical migration.

## Rollback

Downgrade removes the comments added by this revision and leaves all tables,
columns, data, indexes, and constraints unchanged.
