# Error Handling

> How errors are handled in this project.

---

## Overview

The backend uses a small custom exception hierarchy in `app/core/exceptions.py`, then converts those exceptions into JSON responses containing `detail` and `request_id`. Route handlers generally let service-layer exceptions bubble up instead of wrapping them locally.

---

## Error Types

- Base application error: `AppError`
- Common HTTP-shaped subclasses:
  - `NotFoundError`
  - `PermissionDeniedError`
  - `AuthenticationError`
  - `BadRequestError`
  - `ConflictError`
- Resource-specific variants include `UserNotFoundError`, `ItemNotFoundError`, and `RuleDocumentNotFoundError`.

See [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py).

---

## Error Handling Patterns

- Raise domain errors from services when a business rule fails, for example duplicate email, missing user, or forbidden self-delete in [`backend/app/services/user.py`](../../../backend/app/services/user.py).
- Keep route handlers thin and let exceptions bubble to the registered app handlers rather than swallowing them in each route.
- Use `RequestIdMiddleware` so every response, including errors, carries `X-Request-ID`.
- Let unexpected exceptions fall through to `unhandled_exception_handler`, which logs the traceback and returns a generic 500 payload.

---

## API Error Responses

- Custom application errors return:
  - `detail`
  - `request_id`
- Starlette/FastAPI `HTTPException` responses are normalized to the same shape.
- Validation errors return:
  - `detail` as the validation error list
  - `request_id`

The response normalization is implemented in [`backend/app/core/exceptions.py`](../../../backend/app/core/exceptions.py).

---

## Common Mistakes

- Returning ad hoc dict error payloads from routes instead of raising an exception handled by the app.
- Hiding business-rule failures in CRUD helpers instead of surfacing them clearly from services.
- Logging and re-raising the same expected application error repeatedly when the global handlers already shape the response.
