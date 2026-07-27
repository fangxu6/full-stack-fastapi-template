import json
from collections.abc import Callable
from typing import cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import structlog
from pytest import CaptureFixture
from sentry_sdk.types import Event

from app.core.config import settings
from app.core.db import IamBootstrapInitializationError
from app.core.observability import (
    bind_request_context,
    clear_request_context,
    configure_observability,
    log_event,
    normalize_request_id,
    set_actor_kind_authenticated,
    should_sample_success,
)
from app.initial_data import init as init_initial_data
from app.main import scrub_sentry_error, scrub_sentry_transaction
from app.utils import send_email


def test_request_id_normalization_accepts_only_lowercase_hex() -> None:
    request_id = "a" * 32

    assert normalize_request_id(request_id) == request_id
    assert normalize_request_id("A" * 32) != "A" * 32
    assert len(normalize_request_id("not-a-request-id")) == 32


def test_success_sampling_is_stable() -> None:
    request_id = "a" * 32

    assert should_sample_success(request_id) is should_sample_success(request_id)


def test_request_context_contains_only_safe_keys() -> None:
    bind_request_context(request_id="a" * 32)

    assert structlog.contextvars.get_contextvars() == {
        "request_id": "a" * 32,
        "actor_kind": "anonymous",
    }

    set_actor_kind_authenticated()

    assert structlog.contextvars.get_contextvars() == {
        "request_id": "a" * 32,
        "actor_kind": "authenticated",
    }
    clear_request_context()


def test_log_event_emits_only_allowlisted_json(capsys: CaptureFixture[str]) -> None:
    configure_observability()
    bind_request_context(request_id="a" * 32)

    log_event(
        event_name="dependency.failed",
        severity="ERROR",
        dependency="smtp",
        elapsed_ms=23,
    )
    clear_request_context()

    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert payload["event_name"] == "dependency.failed"
    assert payload["severity"] == "ERROR"
    assert payload["request_id"] == "a" * 32
    assert payload["actor_kind"] == "anonymous"
    assert payload["dependency"] == "smtp"
    assert "exception" not in payload
    assert "token" not in payload


def test_log_event_rejects_unknown_fields_before_serialization(
    capsys: CaptureFixture[str],
) -> None:
    configure_observability()
    untyped_log_event = cast(Callable[..., None], log_event)

    with pytest.raises(TypeError, match="unexpected keyword argument 'token'"):
        untyped_log_event(
            event_name="dependency.failed",
            severity="ERROR",
            dependency="smtp",
            token="sentinel-token",
        )

    assert capsys.readouterr().out == ""


def test_log_event_swallows_sink_failures() -> None:
    logger = MagicMock()
    logger.critical.side_effect = OSError("stdout unavailable")

    with patch("app.core.observability._LOGGER", logger):
        log_event(
            event_name="startup.failed", severity="CRITICAL", dependency="postgres"
        )


def test_sentry_scrubbers_remove_sensitive_event_fields() -> None:
    error_payload = scrub_sentry_error(
        cast(
            Event,
            {
                "request": {"data": "password=secret"},
                "exception": {"values": [{"value": "upstream token"}]},
            },
        ),
        {},
    )
    transaction_payload = scrub_sentry_transaction(
        cast(
            Event,
            {
                "request": {"url": "https://example.invalid/?token=secret"},
                "contexts": {"trace": {"trace_id": "a" * 32}},
                "spans": [{"description": "private value"}],
            },
        ),
        {},
    )

    assert error_payload is not None
    assert transaction_payload is not None
    assert "secret" not in str(error_payload)
    assert "upstream token" not in str(error_payload)
    assert "secret" not in str(transaction_payload)
    assert transaction_payload["spans"] == []
    assert transaction_payload["contexts"] == {"trace": {"trace_id": "a" * 32}}


def test_sentry_transaction_discards_an_invalid_trace_id() -> None:
    transaction_payload = scrub_sentry_transaction(
        cast(
            Event,
            {
                "contexts": {"trace": {"trace_id": "trace-token=secret"}},
            },
        ),
        {},
    )

    assert transaction_payload is not None
    assert "contexts" not in transaction_payload
    assert "secret" not in str(transaction_payload)


def test_smtp_failure_emits_only_the_registered_dependency() -> None:
    message = MagicMock()
    message.send.side_effect = OSError("smtp token=secret")

    with (
        patch.object(
            type(settings),
            "emails_enabled",
            new_callable=PropertyMock,
            return_value=True,
        ),
        patch("app.utils.settings.EMAILS_FROM_EMAIL", "sender@example.com"),
        patch("app.utils.emails.message.Message", return_value=message),
        patch("app.utils.log_event") as mock_log_event,
        pytest.raises(OSError, match="smtp token=secret"),
    ):
        send_email(
            email_to="recipient@example.com", subject="private", html_content="body"
        )

    assert mock_log_event.call_args.kwargs == {
        "event_name": "dependency.failed",
        "severity": "ERROR",
        "dependency": "smtp",
    }


def test_initial_data_database_failure_emits_startup_event() -> None:
    with (
        patch("app.initial_data.Session", side_effect=OSError("database unavailable")),
        patch("app.initial_data.log_event") as mock_log_event,
        pytest.raises(OSError, match="database unavailable"),
    ):
        init_initial_data()

    assert mock_log_event.call_args.kwargs == {
        "event_name": "startup.failed",
        "severity": "CRITICAL",
        "dependency": "postgres",
    }


def test_iam_bootstrap_failure_emits_only_iam_event() -> None:
    session = MagicMock()
    session.exec.return_value.first.return_value = MagicMock()
    session_context = MagicMock()
    session_context.__enter__.return_value = session
    session_context.__exit__.return_value = False

    with (
        patch("app.initial_data.Session", return_value=session_context),
        patch(
            "app.core.db.iam_service.ensure_bootstrap_state",
            side_effect=RuntimeError("IAM bootstrap invariant failed"),
        ),
        patch("app.core.db.log_event") as mock_iam_log_event,
        patch("app.initial_data.log_event") as mock_initial_data_log_event,
        pytest.raises(IamBootstrapInitializationError),
    ):
        init_initial_data()

    assert mock_iam_log_event.call_args.kwargs == {
        "event_name": "startup.failed",
        "severity": "CRITICAL",
        "dependency": "iam_bootstrap",
    }
    mock_initial_data_log_event.assert_not_called()
