from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlmodel import Session

from app.core import cache


def test_make_cache_key_uses_the_versioned_prefix() -> None:
    assert cache.make_cache_key("iam", "user-1") == "cache:v1:iam:user-1"

    with pytest.raises(ValueError, match="non-empty"):
        cache.make_cache_key("", "user-1")


def test_get_json_returns_decoded_value_and_records_a_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    redis_client.get.return_value = '{"enabled":true}'
    key = cache.make_cache_key("test", "hit")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    with (
        patch("app.core.cache.current_request_id", return_value="a" * 32),
        patch("app.core.cache.should_sample_success", return_value=True),
        patch("app.core.cache.log_event") as log_event,
    ):
        assert cache.get_json(key) == {"enabled": True}

    assert log_event.call_args.kwargs["cache_operation"] == "read"
    assert log_event.call_args.kwargs["cache_result"] == "hit"
    assert "key" not in log_event.call_args.kwargs


def test_get_json_returns_none_and_records_a_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    redis_client.get.return_value = None
    key = cache.make_cache_key("test", "miss")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    with (
        patch("app.core.cache.current_request_id", return_value="a" * 32),
        patch("app.core.cache.should_sample_success", return_value=True),
        patch("app.core.cache.log_event") as log_event,
    ):
        assert cache.get_json(key) is None

    assert log_event.call_args.kwargs["cache_operation"] == "read"
    assert log_event.call_args.kwargs["cache_result"] == "miss"


def test_get_json_treats_redis_errors_as_a_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    redis_client.get.side_effect = RedisConnectionError("redis unavailable")
    key = cache.make_cache_key("test", "error")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    with patch("app.core.cache.log_event") as log_event:
        assert cache.get_json(key) is None

    assert log_event.call_args.kwargs["cache_operation"] == "read"
    assert log_event.call_args.kwargs["cache_result"] == "error"
    assert "exception" not in log_event.call_args.kwargs


def test_set_and_delete_treat_redis_errors_as_noops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    redis_client.set.side_effect = RedisConnectionError("redis unavailable")
    redis_client.delete.side_effect = RedisConnectionError("redis unavailable")
    key = cache.make_cache_key("test", "write-error")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    with patch("app.core.cache.log_event") as log_event:
        cache.set_json(key, {"enabled": True}, 60)
        cache.delete(key)

    assert [call.kwargs["cache_operation"] for call in log_event.call_args_list] == [
        "write",
        "delete",
    ]
    assert all(
        call.kwargs["cache_result"] == "error" for call in log_event.call_args_list
    )


def test_invalid_json_is_deleted_before_falling_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    redis_client.get.return_value = "not-json"
    key = cache.make_cache_key("test", "invalid-json")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    assert cache.get_json(key) is None
    redis_client.delete.assert_called_once_with(key)


def test_set_json_requires_a_positive_ttl_and_writes_compact_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_client = MagicMock()
    key = cache.make_cache_key("test", "write")
    monkeypatch.setattr(cache, "_redis_client", lambda: redis_client)

    cache.set_json(key, {"enabled": True}, 60)

    redis_client.set.assert_called_once_with(key, '{"enabled":true}', ex=60)
    with pytest.raises(ValueError, match="positive integer"):
        cache.set_json(key, {"enabled": True}, 0)


def test_deferred_invalidations_are_deduplicated_and_drained_after_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_key = cache.make_cache_key("test", "first")
    second_key = cache.make_cache_key("test", "second")
    deleted: list[tuple[str, ...]] = []
    monkeypatch.setattr(cache, "delete", lambda *keys: deleted.append(keys))

    with Session() as session:
        cache.defer_cache_invalidation(session, second_key, first_key)
        cache.defer_cache_invalidation(session, first_key)
        cache.drain_deferred_cache_invalidations(session)

        assert session.info == {}

    assert deleted == [(first_key, second_key)]


def test_record_cache_reload_records_elapsed_time_and_rejects_negative_values() -> None:
    with (
        patch("app.core.cache.current_request_id", return_value="a" * 32),
        patch("app.core.cache.should_sample_success", return_value=True),
        patch("app.core.cache.log_event") as log_event,
    ):
        cache.record_cache_reload(17)

    assert log_event.call_args.kwargs["cache_operation"] == "reload"
    assert log_event.call_args.kwargs["elapsed_ms"] == 17
    with pytest.raises(ValueError, match="non-negative integer"):
        cache.record_cache_reload(-1)
