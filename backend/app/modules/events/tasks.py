"""Celery adapters for event dispatch, execution, and recovery."""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session

from app.core.audit import bind_audit_actor, clear_audit_actor, require_system_actor
from app.core.celery import celery_app
from app.core.db import engine
from app.core.observability import log_event
from app.models import EventDeliveryErrorCategory

from . import service
from .contracts import EventEnvelope, PermanentEventError
from .registry import event_registry


def _now() -> datetime:
    return datetime.now(UTC)


def _fixed_task_error() -> RuntimeError:
    return RuntimeError("event delivery coordination failed")


def _dispatch_one(
    *, delivery_id: int, expected_dispatch_at: datetime, now: datetime
) -> None:
    try:
        celery_app.tasks["events.process_delivery"].delay(delivery_id)
    except Exception:
        try:
            with Session(engine) as session:
                actor_id = require_system_actor(session=session)
                bind_audit_actor(session=session, actor_id=actor_id)
                try:
                    service.release_dispatch(
                        session=session,
                        delivery_id=delivery_id,
                        expected_dispatch_at=expected_dispatch_at,
                        now=now,
                    )
                    session.commit()
                finally:
                    clear_audit_actor(session=session)
        except Exception:
            pass
        log_event(event_name="event.dispatch.failed", severity="ERROR")


def dispatch_due_deliveries(*, now: datetime | None = None) -> None:
    try:
        current = service.utc_now(now)
        with Session(engine) as session:
            actor_id = require_system_actor(session=session)
            bind_audit_actor(session=session, actor_id=actor_id)
            try:
                service.recover_expired_leases(session=session, now=current, limit=100)
                session.commit()
            finally:
                clear_audit_actor(session=session)

        with Session(engine) as session:
            actor_id = require_system_actor(session=session)
            bind_audit_actor(session=session, actor_id=actor_id)
            try:
                claims = service.claim_dispatchable_deliveries(
                    session=session,
                    now=current,
                    limit=100,
                )
                session.commit()
            finally:
                clear_audit_actor(session=session)
        for delivery_id, expected_dispatch_at in claims:
            _dispatch_one(
                delivery_id=delivery_id,
                expected_dispatch_at=expected_dispatch_at,
                now=current,
            )
    except Exception:
        raise _fixed_task_error() from None


def _copy_delivery_inputs(
    delivery_id: int,
) -> tuple[uuid.UUID, datetime, str, EventEnvelope] | None:
    try:
        with Session(engine) as session:
            claimed = service.claim_execution(session=session, delivery_id=delivery_id)
            if claimed is None:
                return None
            loaded = service.load_event_envelope(
                session=session, delivery_id=delivery_id
            )
            if loaded is None:
                session.rollback()
                raise _fixed_task_error()
            _delivery, envelope = loaded
            if claimed.lease_token is None or claimed.lease_expires_at is None:
                session.rollback()
                raise _fixed_task_error()
            lease_token = claimed.lease_token
            lease_expires_at = claimed.lease_expires_at
            handler_key = claimed.handler_key
            session.commit()
            return lease_token, lease_expires_at, handler_key, envelope
    except RuntimeError as error:
        if str(error) == "event delivery coordination failed":
            raise
        raise _fixed_task_error() from None
    except Exception:
        raise _fixed_task_error() from None


def process_delivery(delivery_id: int) -> None:
    if (
        isinstance(delivery_id, bool)
        or not isinstance(delivery_id, int)
        or delivery_id <= 0
    ):
        raise ValueError("event delivery id must be a positive integer")
    claimed = _copy_delivery_inputs(delivery_id)
    if claimed is None:
        return
    lease_token, _lease_expires_at, handler_key, envelope = claimed
    handler_registration = event_registry.get(handler_key)
    if handler_registration is None:
        category = EventDeliveryErrorCategory.HANDLER_NOT_REGISTERED
    elif handler_registration.event_type != envelope.event_type:
        category = EventDeliveryErrorCategory.HANDLER_EVENT_TYPE_MISMATCH
    elif envelope.schema_version not in handler_registration.schema_versions:
        category = EventDeliveryErrorCategory.SCHEMA_VERSION_UNSUPPORTED
    else:
        category = None
        try:
            handler_registration.handler(envelope.model_copy(deep=True))
        except PermanentEventError:
            category = EventDeliveryErrorCategory.HANDLER_REJECTED
        except Exception:
            category = EventDeliveryErrorCategory.HANDLER_EXECUTION_FAILED
    failure_state: str | None = None
    try:
        with Session(engine) as session:
            if category is None:
                result = service.complete_delivery(
                    session=session,
                    delivery_id=delivery_id,
                    lease_token=lease_token,
                )
                session.commit()
                if result is not None:
                    log_event(event_name="event.delivery.completed", severity="INFO")
                return
            result = service.fail_delivery(
                session=session,
                delivery_id=delivery_id,
                lease_token=lease_token,
                category=category,
            )
            if result is not None:
                failure_state = result.state.value
            session.commit()
    except Exception:
        raise _fixed_task_error() from None
    if result is not None:
        log_event(
            event_name=(
                "event.delivery.retry_wait"
                if failure_state == "RETRY_WAIT"
                else "event.delivery.failed"
            ),
            severity="ERROR",
        )


@celery_app.task(name="events.scan_due_deliveries", ignore_result=True)  # type: ignore[untyped-decorator]
def scan_due_deliveries() -> None:
    dispatch_due_deliveries()


@celery_app.task(name="events.process_delivery", ignore_result=True)  # type: ignore[untyped-decorator]
def process_delivery_task(delivery_id: int) -> None:
    process_delivery(delivery_id)


@celery_app.task(name="events.recover_expired_leases", ignore_result=True)  # type: ignore[untyped-decorator]
def recover_expired_leases_task() -> None:
    dispatch_due_deliveries()
