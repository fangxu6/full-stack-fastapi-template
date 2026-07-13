from typing import cast

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ExceptionHandler

from app.api.main import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    RequestIdMiddleware,
    app_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
    unhandled_exception_handler,
)


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(AppError, cast(ExceptionHandler, app_exception_handler))
app.add_exception_handler(HTTPException, cast(ExceptionHandler, http_exception_handler))
app.add_exception_handler(
    RequestValidationError,
    cast(ExceptionHandler, request_validation_exception_handler),
)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
