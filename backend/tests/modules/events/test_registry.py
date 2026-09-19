import uuid
from datetime import UTC, datetime

import pytest

from app.modules.events.contracts import (
    EventEnvelope,
    EventHandlerRegistration,
    EventHandlerRegistrationError,
)
from app.modules.events.registry import EventHandlerRegistry


def test_registry_rejects_duplicates_and_freezes() -> None:
    registry = EventHandlerRegistry()
    registration = EventHandlerRegistration(
        handler_key="test.handler",
        event_type="test.changed",
        schema_versions=frozenset({1}),
        handler=lambda _envelope: None,
    )
    registry.register(registration)
    with pytest.raises(EventHandlerRegistrationError):
        registry.register(registration)
    registry.freeze()
    with pytest.raises(EventHandlerRegistrationError):
        registry.register(
            EventHandlerRegistration(
                handler_key="test.other",
                event_type="test.changed",
                schema_versions=frozenset({1}),
                handler=lambda _envelope: None,
            )
        )


def test_registry_matches_exact_type_and_version() -> None:
    registry = EventHandlerRegistry()
    registry.register(
        EventHandlerRegistration(
            handler_key="test.handler",
            event_type="test.changed",
            schema_versions=frozenset({1}),
            handler=lambda _envelope: None,
        )
    )
    envelope = EventEnvelope(
        event_id=uuid.uuid4(),
        event_type="test.changed",
        producer="test",
        schema_version=1,
        resource_type="fixture",
        resource_id="case-1",
        occurred_at=datetime.now(UTC),
        payload={},
    )
    assert registry.matching(envelope)[0].handler_key == "test.handler"
