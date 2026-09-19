import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models import (
    AuditEvent,
    EventDelivery,
    EventDeliveryErrorCategory,
    EventDeliveryState,
    EventPublication,
)
from app.modules.events import service
from app.modules.events.contracts import (
    EventEnvelope,
    EventHandlerRegistration,
    EventPublicationConflict,
)
from app.modules.events.registry import event_registry


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


@pytest.fixture(autouse=True)
def clear_event_registry() -> None:
    event_registry.clear_for_testing()
    event_registry.register(
        EventHandlerRegistration(
            handler_key="test.handler",
            event_type="test.changed",
            schema_versions=frozenset({1}),
            handler=lambda _envelope: None,
        )
    )
    yield
    event_registry.clear_for_testing()


def test_publish_is_idempotent_and_freezes_matching_handlers(db: Session) -> None:
    envelope = make_envelope(request_id=None)
    publication = service.publish_event(session=db, envelope=envelope)
    db.commit()

    retry = make_envelope(
        event_id=envelope.event_id,
        occurred_at=envelope.occurred_at,
        request_id="0123456789abcdef0123456789abcdef",
        trace_id="retry-context",
    )
    assert service.publish_event(session=db, envelope=retry).id == publication.id
    db.commit()

    assert (
        len(
            db.exec(
                select(EventPublication).where(
                    EventPublication.event_id == envelope.event_id
                )
            ).all()
        )
        == 1
    )
    assert (
        len(
            db.exec(
                select(EventDelivery).where(
                    EventDelivery.publication_id == publication.id
                )
            ).all()
        )
        == 1
    )


def test_publish_conflict_does_not_rollback_caller_transaction(db: Session) -> None:
    envelope = make_envelope()
    publication = service.publish_event(session=db, envelope=envelope)
    db.commit()

    marker = AuditEvent(
        occurred_at=datetime.now(UTC),
        action="test.marker",
        resource_type="test",
        resource_id=str(uuid.uuid4()),
        changes={"kept": True},
    )
    db.add(marker)
    db.flush()
    with pytest.raises(EventPublicationConflict):
        service.publish_event(
            session=db,
            envelope=make_envelope(
                event_id=envelope.event_id,
                occurred_at=envelope.occurred_at,
                payload={"value": 2},
            ),
        )
    db.commit()

    assert db.get(AuditEvent, marker.id) is not None
    assert db.get(EventPublication, publication.id) is not None


def test_delivery_lease_token_rejects_stale_result_and_accepts_current_result(
    db: Session,
) -> None:
    envelope = make_envelope()
    publication = service.publish_event(session=db, envelope=envelope)
    db.commit()
    delivery = db.exec(
        select(EventDelivery).where(EventDelivery.publication_id == publication.id)
    ).one()
    now = datetime.now(UTC) + timedelta(seconds=1)
    service.claim_dispatchable_deliveries(session=db, now=now)
    db.commit()
    claimed = service.claim_execution(session=db, delivery_id=delivery.id, now=now)
    assert claimed is not None and claimed.lease_token is not None
    token = claimed.lease_token
    db.commit()

    assert (
        service.complete_delivery(
            session=db, delivery_id=delivery.id, lease_token=uuid.uuid4(), now=now
        )
        is None
    )
    db.commit()
    assert (
        service.complete_delivery(
            session=db, delivery_id=delivery.id, lease_token=token, now=now
        )
        is not None
    )
    db.commit()
    final = db.get(EventDelivery, delivery.id)
    assert final is not None
    assert final.state is EventDeliveryState.SUCCEEDED
    assert final.attempt_count == 1


def test_dispatch_lease_release_is_conditional_and_batch_is_bounded(
    db: Session,
) -> None:
    envelope = make_envelope()
    publication = service.publish_event(session=db, envelope=envelope)
    db.commit()
    assert publication.id is not None
    initial = datetime.now(UTC) + timedelta(seconds=1)
    extra_deliveries = [
        EventDelivery(
            publication_id=publication.id,
            handler_key=f"test.handler.{index}",
            state=EventDeliveryState.PENDING,
            attempt_count=0,
            next_attempt_at=initial,
            next_dispatch_at=initial,
        )
        for index in range(101)
    ]
    db.add_all(extra_deliveries)
    db.commit()

    claims = service.claim_dispatchable_deliveries(
        session=db, now=initial, limit=service.DISPATCH_BATCH_SIZE
    )
    assert len(claims) == service.DISPATCH_BATCH_SIZE
    first_id, first_lease = claims[0]
    db.commit()
    second_claims = service.claim_dispatchable_deliveries(
        session=db, now=initial + service.LEASE_DURATION, limit=1
    )
    assert second_claims
    db.commit()

    assert (
        service.release_dispatch(
            session=db,
            delivery_id=first_id,
            expected_dispatch_at=first_lease,
            now=initial,
        )
        is False
    )
    db.rollback()


def test_expired_execution_lease_is_recovered_without_reusing_attempt(
    db: Session,
) -> None:
    publication = service.publish_event(session=db, envelope=make_envelope())
    db.commit()
    delivery = db.exec(
        select(EventDelivery).where(EventDelivery.publication_id == publication.id)
    ).one()
    now = datetime.now(UTC) + timedelta(seconds=1)
    claimed = service.claim_execution(session=db, delivery_id=delivery.id, now=now)
    assert claimed is not None and claimed.lease_expires_at is not None
    expired_at = claimed.lease_expires_at + timedelta(seconds=1)
    db.commit()

    assert (
        service.recover_expired_leases(
            session=db,
            now=expired_at,
            retry_delay=timedelta(0),
        )
        == 1
    )
    db.commit()
    recovered = db.get(EventDelivery, delivery.id)
    assert recovered is not None
    assert recovered.state is EventDeliveryState.RETRY_WAIT
    assert recovered.attempt_count == 1
    assert (
        recovered.last_error_category
        is EventDeliveryErrorCategory.EXECUTION_LEASE_EXPIRED
    )


def test_handler_execution_failure_retries_then_becomes_terminal(
    db: Session,
) -> None:
    envelope = make_envelope()
    publication = service.publish_event(session=db, envelope=envelope)
    db.commit()
    delivery = db.exec(
        select(EventDelivery).where(EventDelivery.publication_id == publication.id)
    ).one()

    now = datetime.now(UTC) + timedelta(seconds=1)
    for _attempt in range(1, service.MAX_ATTEMPTS + 1):
        service.claim_execution(session=db, delivery_id=delivery.id, now=now)
        db.commit()
        refreshed = db.get(EventDelivery, delivery.id)
        assert refreshed is not None and refreshed.lease_token is not None
        service.fail_delivery(
            session=db,
            delivery_id=delivery.id,
            lease_token=refreshed.lease_token,
            category=EventDeliveryErrorCategory.HANDLER_EXECUTION_FAILED,
            now=now,
            retry_delay=timedelta(0),
        )
        db.commit()
        now += timedelta(seconds=1)

    final = db.get(EventDelivery, delivery.id)
    assert final is not None
    assert final.state is EventDeliveryState.FAILED
    assert final.attempt_count == service.MAX_ATTEMPTS
