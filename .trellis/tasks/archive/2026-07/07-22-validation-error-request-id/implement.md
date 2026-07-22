# Implementation Plan: Document request ID in validation errors

1. Inspect the current FastAPI OpenAPI component and platform baseline tests.
2. Add a cached custom OpenAPI wrapper in `backend/app/main.py` that augments
   `components.schemas.HTTPValidationError` with required `request_id: string`
   while retaining the framework-generated schema.
3. Extend the platform baseline test to assert the OpenAPI component and real
   HTTP 422 response/header contract.
4. Regenerate the OpenAPI snapshot and frontend client through the repository's
   generator path; do not hand-edit generated output.
5. Run targeted backend tests, backend lint/type checks as feasible, frontend
   build, read-only frontend lint, generated-file inspection, and diff checks.

## Rollback

Revert the OpenAPI wrapper, its test, and generated artifacts together. The
runtime validation handler is unchanged, so rollback restores only the prior
documentation/type omission.
