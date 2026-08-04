import json
from functools import cache
from time import perf_counter
from typing import Any

from redis import Redis
from redis.exceptions import RedisError
from sqlmodel import Session

from app.core.config import settings
from app.core.observability import (
    CacheOperation,
    CacheResult,
    current_request_id,
    log_event,
    should_sample_success,
)

CACHE_KEY_PREFIX = "cache:v1:"
_DEFERRED_INVALIDATION_KEYS = "app.core.cache.deferred_invalidation_keys"


def make_cache_key(namespace: str, identity: str) -> str:
    if not namespace or not identity:
        raise ValueError("cache namespace and identity must be non-empty")
    return f"{CACHE_KEY_PREFIX}{namespace}:{identity}"


@cache
def _redis_client() -> Redis:
    return Redis.from_url(
        settings.redis_cache_url,
        decode_responses=True,
        socket_connect_timeout=settings.CACHE_REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=settings.CACHE_REDIS_SOCKET_TIMEOUT_SECONDS,
    )


def get_json(key: str) -> Any | None:
    _require_cache_key(key)
    started_at = perf_counter()
    try:
        value = _redis_client().get(key)
    except RedisError, UnicodeError:
        _log_cache_error("read", _elapsed_ms(started_at))
        return None

    if value is None:
        _log_cache_success("read", "miss", _elapsed_ms(started_at))
        return None
    if not isinstance(value, str | bytes | bytearray):
        _log_cache_error("read", _elapsed_ms(started_at))
        delete(key)
        return None

    try:
        decoded = json.loads(value)
    except json.JSONDecodeError, TypeError, UnicodeError:
        _log_cache_error("read", _elapsed_ms(started_at))
        delete(key)
        return None

    _log_cache_success("read", "hit", _elapsed_ms(started_at))
    return decoded


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    _require_cache_key(key)
    if (
        isinstance(ttl_seconds, bool)
        or not isinstance(ttl_seconds, int)
        or ttl_seconds <= 0
    ):
        raise ValueError("cache ttl_seconds must be a positive integer")
    payload = json.dumps(value, separators=(",", ":"), allow_nan=False)
    started_at = perf_counter()
    try:
        _redis_client().set(key, payload, ex=ttl_seconds)
    except RedisError:
        _log_cache_error("write", _elapsed_ms(started_at))
        return
    _log_cache_success("write", "success", _elapsed_ms(started_at))


def delete(*keys: str) -> None:
    if not keys:
        return
    for key in keys:
        _require_cache_key(key)
    started_at = perf_counter()
    try:
        _redis_client().delete(*keys)
    except RedisError:
        _log_cache_error("delete", _elapsed_ms(started_at))
        return
    _log_cache_success("delete", "success", _elapsed_ms(started_at))


def record_cache_reload(elapsed_ms: int) -> None:
    if (
        isinstance(elapsed_ms, bool)
        or not isinstance(elapsed_ms, int)
        or elapsed_ms < 0
    ):
        raise ValueError("cache reload elapsed_ms must be a non-negative integer")
    _log_cache_success("reload", "success", elapsed_ms)


def defer_cache_invalidation(session: Session, *keys: str) -> None:
    if not keys:
        return
    for key in keys:
        _require_cache_key(key)
    deferred = session.info.setdefault(_DEFERRED_INVALIDATION_KEYS, set())
    if not isinstance(deferred, set):
        raise TypeError("cache invalidation registry has an unexpected type")
    deferred.update(keys)


def drain_deferred_cache_invalidations(session: Session) -> None:
    deferred = session.info.pop(_DEFERRED_INVALIDATION_KEYS, set())
    if deferred:
        delete(*sorted(deferred))


def discard_deferred_cache_invalidations(session: Session) -> None:
    session.info.pop(_DEFERRED_INVALIDATION_KEYS, None)


def _require_cache_key(key: str) -> None:
    if not key.startswith(CACHE_KEY_PREFIX):
        raise ValueError(f"cache key must start with {CACHE_KEY_PREFIX}")


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _log_cache_success(
    operation: CacheOperation, result: CacheResult, elapsed_ms: int
) -> None:
    request_id = current_request_id()
    if request_id is None or not should_sample_success(request_id):
        return
    log_event(
        event_name="cache.operation",
        severity="INFO",
        request_id=request_id,
        cache_operation=operation,
        cache_result=result,
        elapsed_ms=elapsed_ms,
    )


def _log_cache_error(operation: CacheOperation, elapsed_ms: int) -> None:
    log_event(
        event_name="cache.operation",
        severity="ERROR",
        request_id=current_request_id(),
        cache_operation=operation,
        cache_result="error",
        elapsed_ms=elapsed_ms,
    )
