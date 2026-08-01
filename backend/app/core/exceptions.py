from time import perf_counter

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.observability import (
    EventName,
    Severity,
    bind_request_context,
    clear_request_context,
    log_event,
    log_exception,
    normalize_request_id,
    should_sample_success,
)

REQUEST_ID_HEADER = "X-Request-ID"


class AppError(Exception):
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Internal Server Error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = HTTP_404_NOT_FOUND
    detail = "Resource not found"


class PermissionDeniedError(AppError):
    status_code = HTTP_403_FORBIDDEN
    detail = "Permission denied"


class AuthenticationError(AppError):
    status_code = HTTP_403_FORBIDDEN
    detail = "Could not validate credentials"


class ItemNotFoundError(NotFoundError):
    detail = "Item not found"


class RuleDocumentNotFoundError(NotFoundError):
    detail = "Rule document not found"


class UserNotFoundError(NotFoundError):
    detail = "User not found"


class BadRequestError(AppError):
    status_code = HTTP_400_BAD_REQUEST
    detail = "Bad request"


class ConflictError(AppError):
    status_code = HTTP_409_CONFLICT
    detail = "Conflict"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = normalize_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        bind_request_context(request_id=request_id)
        started_at = perf_counter()
        status_code = HTTP_500_INTERNAL_SERVER_ERROR

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                if REQUEST_ID_HEADER not in headers:
                    headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
            _log_http_response(
                scope=scope,
                request_id=request_id,
                started_at=started_at,
                status_code=status_code,
            )
        except Exception as exc:
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            log_exception(
                event_name="http.request.failed",
                exception=exc,
                elapsed_ms=elapsed_ms,
                method=scope["method"],
                route_template=getattr(scope.get("route"), "path", "unmatched"),
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            )
            raise
        finally:
            clear_request_context()


def _log_http_response(
    *, scope: Scope, request_id: str, started_at: float, status_code: int
) -> None:
    elapsed_ms = int((perf_counter() - started_at) * 1000)
    route_template = getattr(scope.get("route"), "path", "unmatched")
    threshold = settings.OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS
    is_slow = elapsed_ms >= threshold
    event_name: EventName
    severity: Severity
    if status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
        event_name = "http.request.failed"
        severity = "ERROR"
    else:
        event_name = "http.request.completed"
        severity = "WARNING" if status_code >= 400 else "INFO"
    if status_code >= 400 or is_slow or should_sample_success(request_id):
        log_event(
            event_name=event_name,
            severity=severity,
            elapsed_ms=elapsed_ms,
            slow_threshold_ms=threshold if is_slow else None,
            method=scope["method"],
            route_template=route_template,
            status_code=status_code,
        )


async def unhandled_exception_handler(
    request: Request, _exc: Exception
) -> JSONResponse:
    request_id = normalize_request_id(getattr(request.state, "request_id", None))
    request.state.request_id = request_id
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal Server Error",
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = normalize_request_id(getattr(request.state, "request_id", None))
    request.state.request_id = request_id
    if isinstance(exc, PermissionDeniedError):
        log_event(
            event_name="authorization.denied",
            severity="WARNING",
            actor_kind=getattr(request.state, "actor_kind", "anonymous"),
            authorization_result="denied",
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = normalize_request_id(getattr(request.state, "request_id", None))
    request.state.request_id = request_id
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id, **(exc.headers or {})},
    )


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = normalize_request_id(getattr(request.state, "request_id", None))
    request.state.request_id = request_id
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )
