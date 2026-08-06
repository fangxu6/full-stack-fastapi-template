# Implementation plan

## 1. Prepare the module moves

- Add `units.py` using the existing unit helpers and signatures.
- Add `documents.py` using the existing document/ledger write helpers and
  preserving semantic exceptions and savepoints.
- Keep current entity/schema imports; do not introduce DTOs or migrations.

## 2. Migrate callers

- Update `inventory/router.py` unit endpoints to use `units.py` and document
  write endpoints to use `documents.py`.
- Update `inventory/importer.py` to resolve units through `units.py` and create
  documents through `documents.py`.
- Update `inventory/correction_service.py` to apply approved operations through
  `documents.py`.
- Leave `daily_report.py` on the query function in `service.py`.
- Remove the moved write implementations and obsolete imports from
  `service.py`.

## 3. Tests

- Add or update focused module tests for units and document/ledger invariants.
- Keep existing inventory API, importer, and correction tests as regression
  coverage.
- Search for every moved symbol after migration and assert no production caller
  reaches it through `service.py`.

## 4. Verification

- Run focused backend tests with `POSTGRES_DB=aiadmin_test` or the ignored
  `.env_test` file.
- Run `bash -lc 'cd backend && ./scripts/lint.sh'` from the repository root.
- Review `git diff --check` and confirm no schema/OpenAPI/generated-client,
  migration, dependency, or unrelated formatting changes occurred.
- Run the full relevant inventory test scope before the final quality check.
