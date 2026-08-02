# Implementation: PostgreSQL Chinese Comment Backfill

1. Confirm the Alembic head and add one revision whose `down_revision` is that
   head.
2. Add complete Chinese table and column comment mappings for the 18 managed
   tables and 198 cataloged columns; apply them through Alembic comment
   operations and reverse them in `downgrade`.
3. Run migration import/syntax checks, then upgrade the local database to head.
4. Query `obj_description` and `col_description` to assert 18/18 table and
   198/198 column comments are non-empty and contain Chinese text.
5. Downgrade one revision and verify the comments are cleared, then re-upgrade
   to head and repeat the catalog assertion.
6. Run focused checks and `git diff --check`; record actual results in the PRD.
