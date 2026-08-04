# Cache Guidelines

> Rules for opt-in Redis business caching in `backend/app/**`.

## Scenario: Opt-In Redis Business Cache

### 1. Scope / Trigger

- Trigger: a measured slow business read needs an explicit Cache-Aside path, or
  a write must invalidate a cache key after commit.
- Redis database `0` remains the Celery broker and database `1` remains the
  short-lived Celery result backend. Business cache entries use database `2`.
- PostgreSQL remains the business source of truth. Cached permissions never
  replace server-side `permission_required()` evaluation.

### 2. Signatures

```python
from sqlmodel import Session

from app.core.cache import (
    defer_cache_invalidation,
    delete,
    get_json,
    make_cache_key,
    record_cache_reload,
    set_json,
)

key = make_cache_key("inventory:summary", str(unit_id))
cached = get_json(key)
set_json(key, value, ttl_seconds=60)
record_cache_reload(elapsed_ms=17)
defer_cache_invalidation(session, key)
```

- `Settings.redis_cache_url` builds the Redis database `2` URL from the shared
  host, port, and password configuration.
- `CACHE_REDIS_CONNECT_TIMEOUT_SECONDS` and
  `CACHE_REDIS_SOCKET_TIMEOUT_SECONDS` are positive runtime settings.
- `make_cache_key()` returns keys under the `cache:v1:` prefix; `get_json()`,
  `set_json()`, and `delete()` reject keys outside that prefix.

### 3. Contracts

- Declare `redis` as a direct dependency. Do not rely on the `celery[redis]`
  transitive dependency.
- Cache behavior is opt-in in the owning service. Do not add route middleware,
  automatic decorators, global `get_or_set`, prefix deletion, prewarming, or
  locks without a separate measured need.
- `set_json()` requires a positive integer TTL. Cache reads return `None` for
  a miss, Redis outage, decoding failure, or corrupt JSON; writes and deletes
  are no-ops on Redis errors. The caller still loads the PostgreSQL truth.
- A Cache-Aside caller measures its PostgreSQL reload and calls
  `record_cache_reload()`. It must not give a loader callback to the cache
  primitive.
- Register only exact cache keys with `defer_cache_invalidation()`. HTTP
  `WriteSessionDep` commits first, drains keys second, and discards keys on
  route failure or commit rollback. Celery, CLI, and other transaction owners
  need their own explicit post-commit boundary.
- Cache telemetry uses `cache.operation` with operation, result, and elapsed
  milliseconds. Do not pass a cache key, value, user ID, Redis URL, query,
  raw exception, or credentials to `log_event()`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Cache key lacks `cache:v1:` | Raise `ValueError` before Redis is called. |
| TTL is zero, negative, or not an integer | Raise `ValueError`; do not create an unbounded entry. |
| Redis read fails or returns malformed JSON | Treat as a miss, emit safe error telemetry, and read the source of truth. |
| Redis write or delete fails | Emit safe error telemetry and preserve the successful database response. |
| Write transaction raises or commit fails | Roll back and discard deferred keys without deleting cache entries. |
| Write transaction commits | Delete only registered exact keys after commit. |
| Caller tries to log a key, value, URL, or identity | Closed `log_event()` signature raises `TypeError`. |

### 5. Good / Base / Bad Cases

- Good: a proven slow inventory summary checks one versioned key, reloads
  PostgreSQL on a miss, writes a finite TTL, records the reload duration, and
  registers its exact key after a relevant successful write.
- Base: Redis is unavailable and the same request returns data directly from
  PostgreSQL without exposing Redis errors to the client.
- Bad: cache middleware automatically stores every GET response, a mutation
  runs `FLUSHDB`, or an authorization dependency treats cached permissions as
  the authority.

### 6. Tests Required

- Unit test the database `2` URL, escaped Redis password, and positive timeout
  validation.
- Unit test versioned key construction, JSON hit/miss, finite TTL, malformed
  JSON, and Redis read/write/delete failures.
- Unit test the request unit of work event order: commit then delete; rollback
  or commit failure never deletes.
- Assert telemetry distinguishes hit, miss, reload, and error without allowing
  key, value, URL, or user identity fields.

### 7. Wrong vs Correct

#### Wrong

```python
@cache_response
def get_summary() -> Summary:
    return load_summary()
```

This hides the freshness policy, cache key inputs, source reload timing, and
write-path invalidation.

#### Correct

```python
from time import perf_counter

key = make_cache_key("inventory:summary", str(unit_id))
cached = get_json(key)
if cached is not None:
    return Summary.model_validate(cached)

started_at = perf_counter()
summary = load_summary(session=session, unit_id=unit_id)
record_cache_reload(elapsed_ms=round((perf_counter() - started_at) * 1000))
set_json(key, summary.model_dump(mode="json"), ttl_seconds=60)
return summary
```

The service owns its measured freshness policy and explicit cache invalidation.
