import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlmodel import Session, select

from app.models import EventDelivery, EventDeliveryErrorCategory, EventDeliveryState
from app.modules.events import service, tasks
from app.modules.events.contracts import EventEnvelope, EventHandlerRegistration
from app.modules.events.registry import event_registry


def _make_envelope() -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid4(),
        event_type="test.changed",
        producer="test",
        schema_version=1,
        resource_type="fixture",
        resource_id="case-1",
        occurred_at=datetime.now(UTC),
        payload={"value": 1},
    )


def test_celery_registers_event_tasks_and_beat_schedule() -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "PROJECT_NAME": "Full Stack FastAPI Template",
            "POSTGRES_SERVER": "127.0.0.1",
            "POSTGRES_USER": "app",
            "POSTGRES_PASSWORD": "changethis",
            "POSTGRES_DB": "event_kernel_pytest",
            "FIRST_SUPERUSER": "admin@example.com",
            "FIRST_SUPERUSER_PASSWORD": "changethis",
            "REDIS_HOST": "127.0.0.1",
        }
    )
    script = (
        "from app.core.celery import celery_app\n"
        "celery_app.loader.import_default_modules()\n"
        "assert 'events.scan_due_deliveries' in celery_app.tasks\n"
        "assert 'events.process_delivery' in celery_app.tasks\n"
        "assert 'event-callback-scan-due' in celery_app.conf.beat_schedule\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_worker_rejects_handler_registered_for_another_event_type(db: Session) -> None:
    called = False

    def handler(_envelope: EventEnvelope) -> None:
        nonlocal called
        called = True

    event_registry.clear_for_testing()
    event_registry.register(
        EventHandlerRegistration(
            handler_key="test.handler",
            event_type="test.changed",
            schema_versions=frozenset({1}),
            handler=handler,
        )
    )
    publication = service.publish_event(session=db, envelope=_make_envelope())
    db.commit()
    delivery = db.exec(
        select(EventDelivery).where(EventDelivery.publication_id == publication.id)
    ).one()

    event_registry.clear_for_testing()
    event_registry.register(
        EventHandlerRegistration(
            handler_key="test.handler",
            event_type="test.other",
            schema_versions=frozenset({1}),
            handler=handler,
        )
    )
    try:
        tasks.process_delivery(delivery.id or 0)
    finally:
        event_registry.clear_for_testing()

    db.expire_all()
    persisted = db.get(EventDelivery, delivery.id)
    assert persisted is not None
    assert persisted.state is EventDeliveryState.FAILED
    assert (
        persisted.last_error_category
        is EventDeliveryErrorCategory.HANDLER_EVENT_TYPE_MISMATCH
    )
    assert persisted.attempt_count == 1
    assert called is False
