# Design: Document request ID in validation errors

## Decision

Patch the single shared `HTTPValidationError` component schema when FastAPI
generates OpenAPI. Mark `request_id` as a required string, then regenerate the
committed frontend OpenAPI snapshot and client.

## Why This Boundary

`RequestIdMiddleware` and the global validation handler already guarantee that
every HTTP 422 response has `request_id` in both its JSON body and
`X-Request-ID` header. FastAPI's automatically generated 422 component does
not know about the custom handler, so it documents only `detail`.

Updating the shared component once fixes every route that references
`#/components/schemas/HTTPValidationError`, without adding repeated `responses`
metadata to individual routes.

## Alternatives Rejected

1. Hand-edit `frontend/src/client/types.gen.ts` or `schemas.gen.ts`.
   Generated files would drift on the next client refresh.
2. Add a 422 response model to every route.
   This duplicates one global runtime contract across all routes and misses
   future routes unless each author remembers it.
3. Make `request_id` optional in OpenAPI.
   That would under-document a field the runtime handler always provides.

## Compatibility

- Keep the existing 422 status code and FastAPI validation-error array under
  `detail` unchanged.
- Preserve the existing `X-Request-ID` header behavior.
- Preserve FastAPI's normal OpenAPI generation and caching behavior; mutate the
  completed shared schema only after the framework builds it.

## Validation

- Backend test asserts the OpenAPI component has a required string
  `request_id` and that a real 422 body/header still agree.
- Regeneration updates `frontend/openapi.json` and the generated client files.
- TypeScript build and read-only frontend lint verify generated output.
