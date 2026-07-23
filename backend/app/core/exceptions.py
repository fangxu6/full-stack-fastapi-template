from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.core.config import settings
from app.core.observability import (
    EventName,
    Severity,
    bind_request_context,
    clear_request_context,
    log_event,
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


class ServiceUnavailableError(AppError):
    status_code = HTTP_503_SERVICE_UNAVAILABLE
    detail = "Service unavailable"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        bind_request_context(request_id=request_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            threshold = (
                settings.OBSERVABILITY_AI_SLOW_THRESHOLD_MS
                if route_template == f"{settings.API_V1_STR}/ai/inventory/query"
                else settings.OBSERVABILITY_HTTP_SLOW_THRESHOLD_MS
            )
            is_slow = elapsed_ms >= threshold
            event_name: EventName
            severity: Severity
            if response.status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
                event_name = "http.request.failed"
                severity = "ERROR"
            else:
                event_name = "http.request.completed"
                severity = "WARNING" if response.status_code >= 400 else "INFO"
            if (
                response.status_code >= 400
                or is_slow
                or response.status_code >= HTTP_500_INTERNAL_SERVER_ERROR
                or should_sample_success(request_id)
            ):
                log_event(
                    event_name=event_name,
                    severity=severity,
                    elapsed_ms=elapsed_ms,
                    slow_threshold_ms=threshold if is_slow else None,
                    method=request.method,
                    route_template=route_template,
                    status_code=response.status_code,
                )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            log_event(
                event_name="http.request.failed",
                severity="ERROR",
                elapsed_ms=elapsed_ms,
                method=request.method,
                route_template=getattr(request.scope.get("route"), "path", "unmatched"),
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            )
            raise
        finally:
            clear_request_context()


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
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )
