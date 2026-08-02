# Backfill PostgreSQL Chinese comments

## Goal

Add Chinese PostgreSQL table and column comments to all current model tables through one forward Alembic migration.

## Requirements

- Backfill non-empty Chinese business comments for the 18 current public model
  tables and their 198 physical columns in the configured local PostgreSQL
  database.
- Use one new forward Alembic revision from the current head. It must only
  change PostgreSQL comments and must not modify rows, types, constraints,
  indexes, API contracts, or historical migrations.
- Keep the historical backfill migration self-contained. Existing SQLModel
  metadata remains unchanged; the forward-only model-metadata rule applies to
  tables and columns introduced after this task.
- Support downgrade by removing only the comments created by this revision.

## Acceptance Criteria

- [x] The migration defines an accurate Chinese comment for each of the 18
  model tables and 198 physical columns.
- [x] `upgrade` applies comments without changing any business data or schema
  object shape; `downgrade` removes only these comments.
- [x] On the local database at migration head, catalog checks show all 18
  target tables and all 198 target columns have non-empty Chinese comments.
- [x] The migration chain upgrades and downgrades successfully on the local
  database.
- [x] Focused migration syntax/import checks and `git diff --check` pass.

## Notes

- Comments are based on the current model and live schema inventory captured
  on 2026-08-02: all 18 target tables and 198 target columns lacked comments.
- No API E2E artifact is needed because this task has no API surface.
- Verified on the local database: upgrade, downgrade, and final re-upgrade
  completed successfully; the final catalog matched all 18 table and 198
  column comments exactly.
