# Error Handling

> Unified backend error rules for this repository.

---

## Overview

Unified error handling is already a real platform baseline in this repo. It is not optional guidance. Future backend work must preserve the centralized error contract, request correlation, and traceback logging behavior.

---

## Current Reality

- `RequestIdMiddleware` generates or propagates `X-Request-ID` and writes it back to the response:
  - [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
  - [`backend/app/main.py`](../../../backend/app/main.py)
- The application registers global handlers for:
  - `AppError`
  - FastAPI/Starlette `HTTPException`
  - `RequestValidationError`
  - unhandled `Exception`
- All of those paths return a JSON body containing:
  - `detail`
  - `request_id`
- The response header also carries `X-Request-ID`.

---

## Required Contract

All backend error responses must converge to:

```json
{
  "detail": "...",
  "request_id": "..."
}
```

This applies to:

- business errors raised as `AppError` subclasses
- auth/permission failures
- framework-level `401/404`
- validation `422`
- unexpected `500`

## OpenAPI Contract

FastAPI's default `HTTPValidationError` schema describes only the validation
`detail` array. Because this project adds `request_id` in its global validation
handler, `RequestIdOpenAPIFastAPI.openapi()` must also expose `request_id` as a
required string on that shared component. After changing the error contract,
regenerate `frontend/src/client/**` through `bash ./scripts/generate-client.sh`;
do not hand-edit generated client types.

---

## Exception Usage Rules

- Prefer semantic `AppError` subclasses from [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py), such as:
  - `UserNotFoundError`
  - `ItemNotFoundError`
  - `RuleDocumentNotFoundError`
  - `PermissionDeniedError`
  - `BadRequestError`
  - `ConflictError`
- Raise service-layer domain exceptions and let them bubble to the global handlers:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Keep route handlers focused on delegating to services; do not catch domain exceptions in each route just to rebuild the same response payload.
- Do not normalize errors ad hoc in every route.

---

## 500 and Traceback Rules

- Unified JSON does not mean swallowing diagnostics.
- Unexpected exceptions must still log traceback server-side with request correlation:
  - [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- The minimum failure trail for a real bug is:
  - response body `request_id`
  - response header `X-Request-ID`
  - one stdout NDJSON `http.request.failed` record with `request_id`, method,
    route template, status, elapsed time, and the original traceback in
    `exception`

---

## Current Reality vs Recommended Direction

### Current reality

- The repo already centralizes the error pipeline correctly.
- Services already use semantic exceptions in multiple places:
  - [`backend/app/services/user.py`](../../../backend/app/services/user.py)
  - [`backend/app/services/docs.py`](../../../backend/app/services/docs.py)

### Recommended direction

- When new business rules appear, add a new `AppError` subclass if existing semantics are not clear enough.
- Avoid long-term service-layer use of ad hoc `HTTPException` or plain `Exception` for expected business failures.

---

## Forbidden Regressions

- Do not return temporary route-local error payloads with a different shape.
- Do not lose `request_id` on `401/404/422/500`.
- Do not convert 500 responses into opaque generic errors without traceback logging.
- Do not add frontend-only assumptions that require a different error body shape from the backend baseline.

---

## Code Anchors

- Global registration: [`backend/app/main.py`](../../../backend/app/main.py)
- Exception hierarchy and handlers: [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py)
- Service usage: [`backend/app/services/user.py`](../../../backend/app/services/user.py), [`backend/app/services/item.py`](../../../backend/app/services/item.py)
- Frontend request/error consumer context: [`frontend/src/main.tsx`](../../../frontend/src/main.tsx), [`frontend/src/shared/utils/index.ts`](../../../frontend/src/shared/utils/index.ts)
