"""Test-only handler assembly for the real event worker test."""

from sqlmodel import Session, select

from app.core.audit import bind_audit_actor, clear_audit_actor, require_system_actor
from app.core.db import engine
from app.models import AuditEvent
from app.modules.audit.service import append_audit_event
from app.modules.events.contracts import EventEnvelope, EventHandlerRegistration
from app.modules.events.registry import event_registry

HANDLER_KEY = "test.runtime.handler"
AUDIT_ACTION = "test.event.handler"


def runtime_handler(envelope: EventEnvelope) -> None:
    with Session(engine) as session:
        actor_id = require_system_actor(session=session)
        bind_audit_actor(session=session, actor_id=actor_id)
        try:
            resource_id = str(envelope.event_id)
            existing = session.exec(
                select(AuditEvent).where(
                    AuditEvent.action == AUDIT_ACTION,
                    AuditEvent.resource_id == resource_id,
                )
            ).first()
            if existing is None:
                append_audit_event(
                    session=session,
                    actor_user_id=actor_id,
                    request_id=envelope.request_id,
                    action=AUDIT_ACTION,
                    resource_type="test_event",
                    resource_id=resource_id,
                    changes={"handled": True},
                )
            session.commit()
        finally:
            clear_audit_actor(session=session)


def register_runtime_handler() -> None:
    event_registry.register(
        EventHandlerRegistration(
            handler_key=HANDLER_KEY,
            event_type="test.runtime.changed",
            schema_versions=frozenset({1}),
            handler=runtime_handler,
        )
    )
