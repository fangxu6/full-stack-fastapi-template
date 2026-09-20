import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.modules.events.contracts import (
    MAX_PAYLOAD_BYTES,
    EventContractError,
    EventEnvelope,
    EventHandlerRegistration,
    PermanentEventError,
    normalize_payload,
)


def make_envelope(**overrides: object) -> EventEnvelope:
    values: dict[str, object] = {
        "event_id": uuid.uuid4(),
        "event_type": "test.changed",
        "producer": "test",
        "schema_version": 1,
        "resource_type": "fixture",
        "resource_id": "case-1",
        "occurred_at": datetime(2026, 9, 19, tzinfo=UTC),
        "payload": {"value": 1},
    }
    values.update(overrides)
    return EventEnvelope.model_validate(values)


def test_envelope_normalizes_timestamp_and_copies_nested_payload() -> None:
    payload = {"nested": {"value": 1}}
    envelope = make_envelope(
        occurred_at=datetime(2026, 9, 19, 8, tzinfo=UTC), payload=payload
    )

    payload["nested"]["value"] = 2  # type: ignore[index]

    assert envelope.occurred_at == datetime(2026, 9, 19, 8, tzinfo=UTC)
    assert envelope.payload == {"nested": {"value": 1}}
    envelope.payload["nested"]["value"] = 3  # type: ignore[index]
    assert payload == {"nested": {"value": 2}}


def test_payload_rejects_non_json_values_and_bounds() -> None:
    with pytest.raises(EventContractError):
        normalize_payload({"value": object()})
    with pytest.raises(EventContractError):
        normalize_payload({"value": "x" * (MAX_PAYLOAD_BYTES + 1)})


def test_envelope_rejects_unknown_fields_and_invalid_request_context() -> None:
    with pytest.raises(ValidationError):
        make_envelope(extra=True)
    with pytest.raises(ValidationError):
        make_envelope(request_id="not-a-request-id")
    with pytest.raises(ValidationError):
        make_envelope(trace_id=" ")


def test_registration_rejects_invalid_codes_and_accepts_permanent_error() -> None:
    def handler(_envelope: EventEnvelope) -> None:
        raise PermanentEventError

    registration = EventHandlerRegistration(
        handler_key="test.handler",
        event_type="test.changed",
        schema_versions=frozenset({1}),
        handler=handler,
    )
    assert registration.handler is handler
    with pytest.raises(ValidationError):
        EventHandlerRegistration(
            handler_key="bad key",
            event_type="test.changed",
            schema_versions=frozenset({1}),
            handler=handler,
        )
