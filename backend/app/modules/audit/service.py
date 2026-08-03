import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlmodel import Session, col

from app.models import AuditEvent
from app.models.base import get_datetime_utc

RETENTION_DAYS = 365


def append_audit_event(
    *,
    session: Session,
    actor_user_id: uuid.UUID | None,
    request_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str,
    changes: dict[str, object],
) -> None:
    if not isinstance(changes, dict):
        raise TypeError("audit changes must be an object")
    session.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            request_id=request_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
        )
    )


def cleanup_expired_events(*, session: Session, now: datetime | None = None) -> int:
    cutoff = (now or get_datetime_utc()) - timedelta(days=RETENTION_DAYS)
    result = session.exec(
        delete(AuditEvent).where(col(AuditEvent.occurred_at) < cutoff)
    )
    return result.rowcount or 0
