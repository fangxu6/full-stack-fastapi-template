import hashlib
import logging
import re
import sys
from collections.abc import MutableMapping
from types import TracebackType
from typing import Any, Literal
from uuid import UUID, uuid4

import structlog

from app.core.config import settings

CacheOperation = Literal["read", "write", "delete", "reload"]
CacheResult = Literal["hit", "miss", "success", "error"]
EventName = Literal[
    "cache.operation",
    "http.request.completed",
    "http.request.failed",
    "authorization.denied",
    "dependency.failed",
    "dependency.slow",
    "scheduler.alert.unsent",
    "scheduler.enqueue.failed",
    "startup.failed",
    "task.started",
    "task.completed",
    "task.failed",
]
Severity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
DetailedErrorEventName = Literal["http.request.failed", "task.failed"]

REQUEST_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
TASK_ID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
TASK_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
DEPENDENCIES = {"postgres", "iam_bootstrap", "smtp"}
CACHE_OPERATIONS = {"read", "write", "delete", "reload"}
CACHE_RESULTS = {"hit", "miss", "success", "error"}
_LOGGER = structlog.get_logger("app.observability")


def normalize_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def normalize_task_id(value: object | None) -> str | None:
    if not isinstance(value, str) or not TASK_ID_PATTERN.fullmatch(value):
        return None
    try:
        return value if str(UUID(value)) == value else None
    except ValueError:
        return None


def normalize_task_name(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    if value.startswith("celery.") or not TASK_NAME_PATTERN.fullmatch(value):
        return None
    return value


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
            structlog.processors.format_exc_info,
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


def bind_task_context(*, task_id: str, task_name: str) -> bool:
    safe_task_id = normalize_task_id(task_id)
    safe_task_name = normalize_task_name(task_name)
    clear_task_context()
    if safe_task_id is None or safe_task_name is None:
        return False
    structlog.contextvars.bind_contextvars(
        task_id=safe_task_id,
        task_name=safe_task_name,
    )
    return True


def has_task_context() -> bool:
    context = structlog.contextvars.get_contextvars()
    return (
        normalize_task_id(context.get("task_id")) is not None
        and normalize_task_name(context.get("task_name")) is not None
    )


def set_actor_kind_authenticated() -> None:
    structlog.contextvars.bind_contextvars(actor_kind="authenticated")


def clear_request_context() -> None:
    structlog.contextvars.clear_contextvars()


def clear_task_context() -> None:
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
    cache_operation: CacheOperation | None = None,
    cache_result: CacheResult | None = None,
) -> None:
    if dependency is not None and dependency not in DEPENDENCIES:
        return
    if (
        (event_name == "cache.operation")
        != (cache_operation is not None and cache_result is not None)
        or (cache_operation is not None and cache_operation not in CACHE_OPERATIONS)
        or (cache_result is not None and cache_result not in CACHE_RESULTS)
    ):
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
        "cache_operation": cache_operation,
        "cache_result": cache_result,
    }
    try:
        getattr(_LOGGER, severity.lower())(
            event_name,
            **{key: value for key, value in fields.items() if value is not None},
        )
    except Exception:
        pass


def log_exception(
    *,
    event_name: DetailedErrorEventName,
    exception: BaseException,
    traceback: TracebackType | None = None,
    elapsed_ms: int | None = None,
    method: str | None = None,
    route_template: str | None = None,
    status_code: int | None = None,
) -> None:
    fields = {
        "severity": "ERROR",
        "elapsed_ms": elapsed_ms,
        "method": method,
        "route_template": route_template,
        "status_code": status_code,
    }
    try:
        _LOGGER.error(
            event_name,
            exc_info=(
                type(exception),
                exception,
                traceback or exception.__traceback__,
            ),
            **{key: value for key, value in fields.items() if value is not None},
        )
    except Exception:
        pass
