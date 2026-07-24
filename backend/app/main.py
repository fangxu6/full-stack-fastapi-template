import re
from datetime import datetime
from typing import Any, cast

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sentry_sdk.types import Event
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
from app.core.observability import configure_observability, current_request_id

SENTRY_TRACE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def custom_generate_unique_id(route: APIRoute) -> str:
    tag = route.tags[0] if route.tags else "default"
    return f"{tag}-{route.name}"


class RequestIdOpenAPIFastAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        openapi_schema = super().openapi()
        validation_error = openapi_schema["components"]["schemas"][
            "HTTPValidationError"
        ]
        validation_error["properties"]["request_id"] = {
            "title": "Request Id",
            "type": "string",
        }
        required = validation_error.setdefault("required", [])
        if "request_id" not in required:
            required.append("request_id")
        return openapi_schema


configure_observability()


def scrub_sentry_error(_event: Event, _: dict[str, Any]) -> Event | None:
    try:
        tags = _sentry_tags("http.request.failed")
        return {
            "level": "error",
            "message": "http.request.failed",
            "tags": tags,
        }
    except Exception:
        return None


def scrub_sentry_transaction(event: Event, _: dict[str, Any]) -> Event | None:
    try:
        safe_event: Event = {
            "type": "transaction",
            "transaction": "http.request",
            "transaction_info": {"source": "custom"},
            "spans": [],
            "tags": _sentry_tags("http.request.completed"),
        }
        for field in ("start_timestamp", "timestamp"):
            value = event.get(field)
            if isinstance(value, datetime):
                safe_event[field] = value
        trace_id = event.get("contexts", {}).get("trace", {}).get("trace_id")
        if isinstance(trace_id, str) and SENTRY_TRACE_ID_PATTERN.fullmatch(trace_id):
            safe_event["contexts"] = {"trace": {"trace_id": trace_id}}
        return safe_event
    except Exception:
        return None


def _sentry_tags(event_name: str) -> dict[str, str]:
    tags = {"environment": settings.ENVIRONMENT, "event_name": event_name}
    if request_id := current_request_id():
        tags["request_id"] = request_id
    return tags


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        enable_tracing=True,
        send_default_pii=False,
        before_send=scrub_sentry_error,
        before_send_transaction=scrub_sentry_transaction,
    )

app = RequestIdOpenAPIFastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)
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
app.add_middleware(RequestIdMiddleware)

app.include_router(api_router, prefix=settings.API_V1_STR)
