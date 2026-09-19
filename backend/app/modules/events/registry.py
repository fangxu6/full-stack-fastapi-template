"""Explicit, process-local event handler declarations."""

from collections.abc import Iterable
from threading import RLock

from .contracts import (
    EventEnvelope,
    EventHandlerRegistration,
    EventHandlerRegistrationError,
)


class EventHandlerRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._registrations: dict[str, EventHandlerRegistration] = {}
        self._frozen = False

    def register(self, registration: EventHandlerRegistration) -> None:
        with self._lock:
            if self._frozen:
                raise EventHandlerRegistrationError("event handler registry is frozen")
            if registration.handler_key in self._registrations:
                raise EventHandlerRegistrationError("event handler key is duplicated")
            self._registrations[registration.handler_key] = registration

    def register_many(self, registrations: Iterable[EventHandlerRegistration]) -> None:
        for registration in registrations:
            self.register(registration)

    def freeze(self) -> None:
        with self._lock:
            self._frozen = True

    def clear_for_testing(self) -> None:
        with self._lock:
            self._registrations.clear()
            self._frozen = False

    def get(self, handler_key: str) -> EventHandlerRegistration | None:
        with self._lock:
            return self._registrations.get(handler_key)

    def matching(self, envelope: EventEnvelope) -> tuple[EventHandlerRegistration, ...]:
        with self._lock:
            return tuple(
                registration
                for registration in self._registrations.values()
                if registration.event_type == envelope.event_type
                and envelope.schema_version in registration.schema_versions
            )


event_registry = EventHandlerRegistry()

__all__ = ["EventHandlerRegistration", "EventHandlerRegistry", "event_registry"]
