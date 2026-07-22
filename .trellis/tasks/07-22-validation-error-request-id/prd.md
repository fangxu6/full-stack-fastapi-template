# Document request ID in validation errors

## Goal

Expose request_id in OpenAPI validation-error contract and generated frontend client.

## Confirmed Facts

- The global `RequestValidationError` handler returns HTTP 422 JSON with both
  `detail` and `request_id`; `RequestIdMiddleware` also writes the same value
  to `X-Request-ID`.
- The generated frontend `HTTPValidationError` currently declares only
  `detail`, so the OpenAPI/client contract is incomplete despite the runtime
  response being stable.
- Existing platform-baseline tests assert that validation responses contain
  `request_id`, but do not inspect the generated OpenAPI schema or client type.
- The repository generator exposes pre-existing client drift for AI and
  inventory APIs: the current backend OpenAPI has outpaced the committed client
  output. The generated `request_id` update shares generated files with that
  unrelated drift and cannot be safely hand-isolated.

## Requirements

1. Expose `request_id: string` in the OpenAPI schema used for HTTP 422
   validation responses.
2. Regenerate the frontend client through the repository generator; do not
   hand-edit generated files.
3. Preserve existing 422 `detail` validation-error semantics and the runtime
   response/header contract.
4. Add focused regression coverage for the OpenAPI schema and generated type
   contract where practical.
5. Preserve unrelated user worktree changes.
6. Keep pre-existing generated-client drift in a separately acknowledged commit
   or task; do not silently attribute it to this focused error-contract fix.

## Acceptance Criteria

- [x] `/api/v1/openapi.json` describes `HTTPValidationError` with
  `request_id` as a string.
- [x] `frontend/src/client/types.gen.ts` contains the regenerated
  `HTTPValidationError.request_id` field.
- [x] A real 422 response still contains both `detail` and `request_id`, with
  matching `X-Request-ID` response header.
- [x] Relevant backend tests, frontend type/lint validation, and generated
  client checks pass or have a documented environment blocker.
- [x] No unrelated user files are modified or staged.

## Out of Scope

- Redesigning all successful response bodies into a global envelope.
- Changing the existing `detail` shape for validation failures.
- Altering non-validation error response documentation beyond what is necessary
  for the shared contract.

## Delivery Decision

Commit the full regenerated frontend client first as an explicit synchronization
commit. Commit the `request_id` OpenAPI implementation, regression test, and
task artifacts second. Keep the tracked root `openapi.json` unchanged because
the repository generator treats it as a temporary source file and moves its
fresh output to ignored `frontend/openapi.json`.
