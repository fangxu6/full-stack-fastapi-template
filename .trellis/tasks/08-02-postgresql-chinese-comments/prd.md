# Require Chinese PostgreSQL comments

## Goal

Require every newly created PostgreSQL table and every newly added physical
column to carry an accurate, non-empty Chinese database comment.

## Requirements

- Update the repository database rule and backend Trellis database guideline.
- Persist comments as PostgreSQL `COMMENT` metadata through SQLModel/
  SQLAlchemy and the reviewed Alembic revision; Python comments and OpenAPI
  metadata do not satisfy the requirement.
- Require comments for inherited physical audit columns on new tables, with
  shared definitions owned by `AuditFields` rather than duplicated per model.
- Require migration review and an isolated-database verification using
  PostgreSQL catalog comment functions.
- Keep the rule forward-only. Do not edit existing tables, historical
  migrations, runtime behavior, public APIs, or frontend contracts.

## Acceptance Criteria

- [x] `docs/rules/数据库规则.md` defines the scope, SQLModel expression,
  migration-review obligation, exclusions, and the catalog-based check.
- [x] `.trellis/spec/backend/database-guidelines.md` gives backend developers
  the same enforceable model and migration requirements.
- [x] Both documents require non-empty Chinese business semantics for each new
  table and physical column, including inherited audit columns.
- [x] Both documents explicitly preserve historical schema and migration
  history.
- [x] Documentation changes pass `git diff --check`.

## Notes

- This is a lightweight PRD-only documentation task.
- No new dependency, CI parser, migration, or database backfill is in scope.
