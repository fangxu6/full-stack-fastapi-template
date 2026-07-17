import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

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

REQUEST_ID_HEADER = "X-Request-ID"
logger = logging.getLogger(__name__)


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
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    request.state.request_id = request_id
    logger.error(
        "Unhandled exception for request_id=%s path=%s",
        request_id,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal Server Error",
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    request.state.request_id = request_id
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
    request_id = getattr(request.state, "request_id", str(uuid4()))
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
    request_id = getattr(request.state, "request_id", str(uuid4()))
    request.state.request_id = request_id
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "request_id": request_id,
        },
        headers={REQUEST_ID_HEADER: request_id},
    )
