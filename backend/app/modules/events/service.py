"""Transactional event publication and delivery lifecycle operations."""

import copy
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.audit import (
    AUDIT_ACTOR_SESSION_KEY,
    bind_audit_actor,
    require_system_actor,
)
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models import (
    EventDelivery,
    EventDeliveryErrorCategory,
    EventDeliveryState,
    EventPublication,
)
from app.models.base import get_datetime_utc
from app.modules.audit.service import append_audit_event

from .contracts import EventEnvelope, EventPublicationConflict
from .registry import event_registry

MAX_ATTEMPTS = 8
RETRY_DELAY = timedelta(minutes=15)
DISPATCH_BATCH_SIZE = 100
LEASE_DURATION = timedelta(seconds=settings.CELERY_VISIBILITY_TIMEOUT_SECONDS)
PUBLICATION_AUDIT_ACTION = "event.publication.created"
DELIVERY_AUDIT_ACTIONS = frozenset(
    {
        "event.delivery.claimed",
        "event.delivery.completed",
        "event.delivery.retry_wait",
        "event.delivery.failed",
        "event.delivery.lease_expired",
    }
)


class EventDeliveryNotFoundError(NotFoundError):
    detail = "Event delivery not found"


def utc_now(value: datetime | None = None) -> datetime:
    current = value or get_datetime_utc()
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("event timestamps must be timezone-aware")
    return current.astimezone(UTC)


def _publication_semantics(
    publication: EventPublication,
) -> tuple[object, ...]:
    return (
        publication.event_type,
        publication.schema_version,
        publication.producer,
        publication.resource_type,
        publication.resource_id,
        publication.occurred_at,
        publication.idempotency_key,
        publication.payload,
    )


def _envelope_semantics(envelope: EventEnvelope) -> tuple[object, ...]:
    return (
        envelope.event_type,
        envelope.schema_version,
        envelope.producer,
        envelope.resource_type,
        envelope.resource_id,
        envelope.occurred_at,
        envelope.idempotency_key,
        envelope.payload,
    )


def _append_publication_audit(
    *, session: Session, publication: EventPublication, delivery_count: int
) -> None:
    if publication.id is None:
        raise RuntimeError("event publication must be persisted before auditing")
    changes: dict[str, object] = {
        "event_id": str(publication.event_id),
        "publication_id": publication.id,
        "delivery_count": delivery_count,
    }
    if set(changes) != {"event_id", "publication_id", "delivery_count"}:
        raise RuntimeError("event publication audit contract is invalid")
    append_audit_event(
        session=session,
        actor_user_id=publication.created_by,
        request_id=publication.request_id,
        action=PUBLICATION_AUDIT_ACTION,
        resource_type="event_publication",
        resource_id=str(publication.id),
        changes=changes,
    )


def _append_delivery_audit(
    *,
    session: Session,
    publication: EventPublication,
    delivery: EventDelivery,
    action: str,
) -> None:
    if publication.id is None or delivery.id is None:
        raise RuntimeError("event delivery must be persisted before auditing")
    if action not in DELIVERY_AUDIT_ACTIONS:
        raise RuntimeError("event delivery audit action is not registered")
    changes: dict[str, object] = {
        "event_id": str(publication.event_id),
        "publication_id": publication.id,
        "delivery_id": delivery.id,
        "handler_key": delivery.handler_key,
        "state": delivery.state.value,
        "attempt": delivery.attempt_count,
    }
    if delivery.last_error_category is not None:
        changes["error_category"] = delivery.last_error_category.value
    allowed_keys = {
        "event_id",
        "publication_id",
        "delivery_id",
        "handler_key",
        "state",
        "attempt",
        "error_category",
    }
    if not set(changes) <= allowed_keys:
        raise RuntimeError("event delivery audit contract is invalid")
    append_audit_event(
        session=session,
        actor_user_id=delivery.updated_by,
        request_id=publication.request_id,
        action=action,
        resource_type="event_delivery",
        resource_id=str(delivery.id),
        changes=changes,
    )


def publish_event(*, session: Session, envelope: EventEnvelope) -> EventPublication:
    """Register an immutable publication and its frozen handler set.

    The caller owns the surrounding transaction. This function never commits or
    rolls back, including when an event-ID race is resolved through a savepoint.
    """

    existing = session.exec(
        select(EventPublication).where(EventPublication.event_id == envelope.event_id)
    ).one_or_none()
    if existing is not None:
        if _publication_semantics(existing) != _envelope_semantics(envelope):
            raise EventPublicationConflict("event_id is already used by another event")
        return existing

    publication = EventPublication(
        event_id=envelope.event_id,
        event_type=envelope.event_type,
        producer=envelope.producer,
        schema_version=envelope.schema_version,
        resource_type=envelope.resource_type,
        resource_id=envelope.resource_id,
        occurred_at=envelope.occurred_at,
        request_id=envelope.request_id,
        trace_id=envelope.trace_id,
        idempotency_key=envelope.idempotency_key,
        payload=copy.deepcopy(envelope.payload),
    )
    try:
        with session.begin_nested():
            session.add(publication)
            session.flush()
    except IntegrityError:
        existing = session.exec(
            select(EventPublication).where(
                EventPublication.event_id == envelope.event_id
            )
        ).one_or_none()
        if existing is None:
            raise
        if _publication_semantics(existing) != _envelope_semantics(envelope):
            raise EventPublicationConflict("event_id is already used by another event")
        return existing

    registrations = event_registry.matching(envelope)
    if publication.id is None:
        raise RuntimeError("event publication must be persisted")
    now = publication.created_at
    for registration in registrations:
        delivery = EventDelivery(
            publication_id=publication.id,
            handler_key=registration.handler_key,
            state=EventDeliveryState.PENDING,
            attempt_count=0,
            next_attempt_at=now,
            next_dispatch_at=now,
        )
        session.add(delivery)
    session.flush()
    deliveries = len(registrations)
    _append_publication_audit(
        session=session, publication=publication, delivery_count=deliveries
    )
    session.flush()
    return publication


def _load_delivery_for_update(
    *, session: Session, delivery_id: int
) -> tuple[EventDelivery, EventPublication] | None:
    delivery = session.exec(
        select(EventDelivery).where(EventDelivery.id == delivery_id).with_for_update()
    ).one_or_none()
    if delivery is None:
        return None
    publication = session.get(EventPublication, delivery.publication_id)
    if publication is None:
        raise RuntimeError("event delivery publication is missing")
    return delivery, publication


def _bind_transition_actor(
    *, session: Session, publication: EventPublication, delivery: EventDelivery
) -> None:
    actor_id = (
        publication.created_by
        if delivery.attempt_count <= 1
        else require_system_actor(session=session)
    )
    bind_audit_actor(session=session, actor_id=actor_id)


def _restore_audit_actor(session: Session, actor_id: object) -> None:
    if actor_id is None:
        session.info.pop(AUDIT_ACTOR_SESSION_KEY, None)
    else:
        session.info[AUDIT_ACTOR_SESSION_KEY] = actor_id


def claim_dispatchable_deliveries(
    *,
    session: Session,
    now: datetime | None = None,
    lease_duration: timedelta = LEASE_DURATION,
    limit: int = DISPATCH_BATCH_SIZE,
) -> list[tuple[int, datetime]]:
    current = utc_now(now)
    deliveries = list(
        session.exec(
            select(EventDelivery)
            .where(
                col(EventDelivery.state).in_(
                    (EventDeliveryState.PENDING, EventDeliveryState.RETRY_WAIT)
                ),
                col(EventDelivery.next_attempt_at) <= current,
                col(EventDelivery.next_dispatch_at) <= current,
                col(EventDelivery.attempt_count) < MAX_ATTEMPTS,
            )
            .order_by(col(EventDelivery.next_attempt_at), col(EventDelivery.id))
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    claims: list[tuple[int, datetime]] = []
    for delivery in deliveries:
        if delivery.id is None or delivery.next_dispatch_at is None:
            raise RuntimeError("event delivery must have dispatch lease fields")
        previous_dispatch_at = delivery.next_dispatch_at
        delivery.next_dispatch_at = current + lease_duration
        session.add(delivery)
        claims.append((delivery.id, previous_dispatch_at))
    if claims:
        session.flush()
    return claims


def claim_dispatchable_delivery_ids(
    *,
    session: Session,
    now: datetime | None = None,
    lease_duration: timedelta = LEASE_DURATION,
    limit: int = DISPATCH_BATCH_SIZE,
) -> list[int]:
    return [
        delivery_id
        for delivery_id, _dispatch_at in claim_dispatchable_deliveries(
            session=session,
            now=now,
            lease_duration=lease_duration,
            limit=limit,
        )
    ]


def release_dispatch(
    *,
    session: Session,
    delivery_id: int,
    expected_dispatch_at: datetime,
    now: datetime | None = None,
) -> bool:
    delivery = session.exec(
        select(EventDelivery).where(EventDelivery.id == delivery_id).with_for_update()
    ).one_or_none()
    if (
        delivery is None
        or delivery.state
        not in {EventDeliveryState.PENDING, EventDeliveryState.RETRY_WAIT}
        or delivery.next_dispatch_at != expected_dispatch_at
    ):
        return False
    current = utc_now(now)
    delivery.next_dispatch_at = current.replace(second=0, microsecond=0) + timedelta(
        minutes=1
    )
    session.add(delivery)
    session.flush()
    return True


def recover_expired_leases(
    *,
    session: Session,
    now: datetime | None = None,
    retry_delay: timedelta = RETRY_DELAY,
    limit: int = DISPATCH_BATCH_SIZE,
) -> int:
    current = utc_now(now)
    deliveries = list(
        session.exec(
            select(EventDelivery)
            .where(
                EventDelivery.state == EventDeliveryState.LEASED,
                col(EventDelivery.lease_expires_at) <= current,
            )
            .order_by(col(EventDelivery.lease_expires_at), col(EventDelivery.id))
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    recovered = 0
    for delivery in deliveries:
        if delivery.id is None or delivery.lease_expires_at is None:
            continue
        publication = session.get(EventPublication, delivery.publication_id)
        if publication is None:
            raise RuntimeError("event delivery publication is missing")
        actor_id = require_system_actor(session=session)
        previous_actor = session.info.get(AUDIT_ACTOR_SESSION_KEY)
        bind_audit_actor(session=session, actor_id=actor_id)
        try:
            delivery.last_error_category = (
                EventDeliveryErrorCategory.EXECUTION_LEASE_EXPIRED
            )
            delivery.lease_token = None
            delivery.lease_expires_at = None
            if delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.state = EventDeliveryState.FAILED
                delivery.failed_at = current
                delivery.next_attempt_at = None
                delivery.next_dispatch_at = None
                action = "event.delivery.failed"
            else:
                delivery.state = EventDeliveryState.RETRY_WAIT
                delivery.failed_at = None
                delivery.next_attempt_at = current + retry_delay
                delivery.next_dispatch_at = current + retry_delay
                action = "event.delivery.lease_expired"
            session.add(delivery)
            session.flush()
            _append_delivery_audit(
                session=session,
                publication=publication,
                delivery=delivery,
                action=action,
            )
        finally:
            _restore_audit_actor(session, previous_actor)
        recovered += 1
    return recovered


def claim_execution(
    *,
    session: Session,
    delivery_id: int,
    now: datetime | None = None,
    lease_duration: timedelta = LEASE_DURATION,
) -> EventDelivery | None:
    loaded = _load_delivery_for_update(session=session, delivery_id=delivery_id)
    if loaded is None:
        return None
    delivery, publication = loaded
    current = utc_now(now)
    if delivery.state in {EventDeliveryState.SUCCEEDED, EventDeliveryState.FAILED}:
        return None
    if delivery.state is EventDeliveryState.LEASED:
        if delivery.lease_expires_at is None or delivery.lease_expires_at > current:
            return None
        return None
    if delivery.next_attempt_at is None or delivery.next_attempt_at > current:
        return None
    if delivery.attempt_count >= MAX_ATTEMPTS:
        return None
    previous_actor = session.info.get(AUDIT_ACTOR_SESSION_KEY)
    _bind_transition_actor(session=session, publication=publication, delivery=delivery)
    try:
        delivery.state = EventDeliveryState.LEASED
        delivery.attempt_count += 1
        delivery.lease_token = uuid.uuid4()
        delivery.lease_expires_at = current + lease_duration
        delivery.next_attempt_at = None
        delivery.next_dispatch_at = None
        session.add(delivery)
        session.flush()
        _append_delivery_audit(
            session=session,
            publication=publication,
            delivery=delivery,
            action="event.delivery.claimed",
        )
        session.flush()
    finally:
        _restore_audit_actor(session, previous_actor)
    return delivery


def _result_is_current(
    *,
    delivery: EventDelivery,
    lease_token: uuid.UUID,
    now: datetime,
) -> bool:
    return (
        delivery.state is EventDeliveryState.LEASED
        and delivery.lease_token == lease_token
        and delivery.lease_expires_at is not None
        and delivery.lease_expires_at > now
    )


def complete_delivery(
    *,
    session: Session,
    delivery_id: int,
    lease_token: uuid.UUID,
    now: datetime | None = None,
) -> EventDelivery | None:
    loaded = _load_delivery_for_update(session=session, delivery_id=delivery_id)
    if loaded is None:
        return None
    delivery, publication = loaded
    current = utc_now(now)
    if not _result_is_current(delivery=delivery, lease_token=lease_token, now=current):
        return None
    previous_actor = session.info.get(AUDIT_ACTOR_SESSION_KEY)
    _bind_transition_actor(session=session, publication=publication, delivery=delivery)
    try:
        delivery.state = EventDeliveryState.SUCCEEDED
        delivery.completed_at = current
        delivery.last_error_category = None
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.next_attempt_at = None
        delivery.next_dispatch_at = None
        session.add(delivery)
        session.flush()
        _append_delivery_audit(
            session=session,
            publication=publication,
            delivery=delivery,
            action="event.delivery.completed",
        )
        session.flush()
    finally:
        _restore_audit_actor(session, previous_actor)
    return delivery


def fail_delivery(
    *,
    session: Session,
    delivery_id: int,
    lease_token: uuid.UUID,
    category: EventDeliveryErrorCategory,
    now: datetime | None = None,
    retry_delay: timedelta = RETRY_DELAY,
) -> EventDelivery | None:
    loaded = _load_delivery_for_update(session=session, delivery_id=delivery_id)
    if loaded is None:
        return None
    delivery, publication = loaded
    current = utc_now(now)
    if not _result_is_current(delivery=delivery, lease_token=lease_token, now=current):
        return None
    previous_actor = session.info.get(AUDIT_ACTOR_SESSION_KEY)
    _bind_transition_actor(session=session, publication=publication, delivery=delivery)
    try:
        delivery.last_error_category = category
        delivery.lease_token = None
        delivery.lease_expires_at = None
        delivery.completed_at = None
        if (
            category
            in {
                EventDeliveryErrorCategory.HANDLER_NOT_REGISTERED,
                EventDeliveryErrorCategory.HANDLER_EVENT_TYPE_MISMATCH,
                EventDeliveryErrorCategory.SCHEMA_VERSION_UNSUPPORTED,
                EventDeliveryErrorCategory.HANDLER_REJECTED,
            }
            or delivery.attempt_count >= MAX_ATTEMPTS
        ):
            delivery.state = EventDeliveryState.FAILED
            delivery.failed_at = current
            delivery.next_attempt_at = None
            delivery.next_dispatch_at = None
            action = "event.delivery.failed"
        else:
            delivery.state = EventDeliveryState.RETRY_WAIT
            delivery.failed_at = None
            delivery.next_attempt_at = current + retry_delay
            delivery.next_dispatch_at = current + retry_delay
            action = "event.delivery.retry_wait"
        session.add(delivery)
        session.flush()
        _append_delivery_audit(
            session=session,
            publication=publication,
            delivery=delivery,
            action=action,
        )
        session.flush()
    finally:
        _restore_audit_actor(session, previous_actor)
    return delivery


def load_event_envelope(
    *, session: Session, delivery_id: int
) -> tuple[EventDelivery, EventEnvelope] | None:
    loaded = _load_delivery_for_update(session=session, delivery_id=delivery_id)
    if loaded is None:
        return None
    delivery, publication = loaded
    envelope = EventEnvelope(
        event_id=publication.event_id,
        event_type=publication.event_type,
        producer=publication.producer,
        schema_version=publication.schema_version,
        resource_type=publication.resource_type,
        resource_id=publication.resource_id,
        occurred_at=publication.occurred_at,
        request_id=publication.request_id,
        trace_id=publication.trace_id,
        idempotency_key=publication.idempotency_key,
        payload=copy.deepcopy(publication.payload),
    )
    return delivery, envelope
