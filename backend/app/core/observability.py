import hashlib
import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any, Literal
from uuid import uuid4

import structlog

from app.core.config import settings

EventName = Literal[
    "http.request.completed",
    "http.request.failed",
    "authorization.denied",
    "dependency.failed",
    "dependency.slow",
    "scheduler.alert.unsent",
    "scheduler.enqueue.failed",
    "startup.failed",
]
Severity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]

REQUEST_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
DEPENDENCIES = {"postgres", "iam_bootstrap", "ai_orchestrator", "smtp"}
_LOGGER = structlog.get_logger("app.observability")


def normalize_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def configure_observability() -> None:
    global _LOGGER

    logging.getLogger().handlers.clear()
    logging.getLogger().setLevel(logging.CRITICAL + 1)
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("uvicorn.error").disabled = True
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            _add_environment,
            _normalize_event_name,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=False,
    )
    _LOGGER = structlog.get_logger("app.observability")


def _add_environment(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["schema_version"] = 1
    return event_dict


def _normalize_event_name(
    _: Any, __: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    event_dict["event_name"] = event_dict.pop("event")
    return event_dict


def bind_request_context(*, request_id: str, actor_kind: str = "anonymous") -> None:
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, actor_kind=actor_kind)


def set_actor_kind_authenticated() -> None:
    structlog.contextvars.bind_contextvars(actor_kind="authenticated")


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()


def current_request_id() -> str | None:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    if isinstance(request_id, str) and REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return None


def should_sample_success(request_id: str) -> bool:
    return int.from_bytes(hashlib.sha256(request_id.encode()).digest()[:8]) % 10 == 0


def log_event(
    *,
    event_name: EventName,
    severity: Severity,
    request_id: str | None = None,
    dependency: str | None = None,
    elapsed_ms: int | None = None,
    slow_threshold_ms: int | None = None,
    method: str | None = None,
    route_template: str | None = None,
    status_code: int | None = None,
    actor_kind: str | None = None,
    authorization_result: Literal["denied"] | None = None,
) -> None:
    if dependency is not None and dependency not in DEPENDENCIES:
        return
    fields = {
        "severity": severity,
        "request_id": request_id,
        "dependency": dependency,
        "elapsed_ms": elapsed_ms,
        "slow_threshold_ms": slow_threshold_ms,
        "method": method,
        "route_template": route_template,
        "status_code": status_code,
        "actor_kind": actor_kind,
        "authorization_result": authorization_result,
    }
    try:
        getattr(_LOGGER, severity.lower())(
            event_name,
            **{key: value for key, value in fields.items() if value is not None},
        )
    except Exception:
        pass
