import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlmodel import Session, col, select

from app.core.audit import bind_audit_actor, require_system_actor
from app.core.config import settings
from app.crud.user import increment_password_reset_version
from app.models import EmailOutbox, EmailOutboxKind, EmailOutboxStatus, User
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    generate_set_password_email,
)

MAX_ATTEMPTS = 8
RETRY_DELAY = timedelta(minutes=15)
LEASE_DURATION = timedelta(seconds=settings.CELERY_VISIBILITY_TIMEOUT_SECONDS)


@dataclass(frozen=True)
class DeliveryPayload:
    outbox_id: int
    recipient: str
    subject: str
    html_content: str
    lease_expires_at: datetime


def utc_now(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("email outbox timestamps must be timezone-aware")
    return current.astimezone(UTC)


def queue_rendered_email(
    *, session: Session, recipient: str, subject: str, html_content: str
) -> EmailOutbox:
    outbox = EmailOutbox(
        kind=EmailOutboxKind.RENDERED,
        recipient=recipient,
        subject=subject,
        html_content=html_content,
        next_attempt_at=utc_now(),
    )
    session.add(outbox)
    session.flush()
    return outbox


def queue_account_set_password_email(*, session: Session, user: User) -> EmailOutbox:
    return _queue_link_email(
        session=session,
        user=user,
        kind=EmailOutboxKind.ACCOUNT_SET_PASSWORD,
    )


def queue_password_recovery_email(*, session: Session, user: User) -> EmailOutbox:
    return _queue_link_email(
        session=session,
        user=user,
        kind=EmailOutboxKind.PASSWORD_RECOVERY,
    )


def _queue_link_email(
    *, session: Session, user: User, kind: EmailOutboxKind
) -> EmailOutbox:
    password_reset_version = increment_password_reset_version(
        session=session, user=user
    )
    outbox = EmailOutbox(
        kind=kind,
        recipient=user.email,
        user_id=user.id,
        password_reset_version=password_reset_version,
        next_attempt_at=utc_now(),
    )
    session.add(outbox)
    session.flush()
    return outbox


def recover_expired_leases(*, session: Session, now: datetime) -> None:
    expired = list(
        session.exec(
            select(EmailOutbox)
            .where(
                EmailOutbox.status == EmailOutboxStatus.LEASED,
                EmailOutbox.lease_expires_at.is_not(None),  # type: ignore[union-attr]  # ty:ignore[unresolved-attribute]
                EmailOutbox.lease_expires_at <= now,  # type: ignore[operator]  # ty:ignore[unsupported-operator]
            )
            .with_for_update(skip_locked=True)
        ).all()
    )
    if not expired:
        return
    bind_audit_actor(session=session, actor_id=require_system_actor(session=session))
    for outbox in expired:
        outbox.lease_expires_at = None
        outbox.last_error_category = "DELIVERY_LEASE_EXPIRED"
        if outbox.attempt_count >= MAX_ATTEMPTS:
            outbox.status = EmailOutboxStatus.FAILED
            outbox.failed_at = now
        else:
            outbox.status = EmailOutboxStatus.RETRY_WAIT
            outbox.next_attempt_at = now
        session.add(outbox)


def due_outbox_ids(*, session: Session, now: datetime) -> list[int]:
    return [
        outbox_id
        for outbox_id in session.exec(
            select(EmailOutbox.id)
            .where(
                EmailOutbox.status.in_(  # type: ignore[attr-defined]  # ty:ignore[unresolved-attribute]
                    [EmailOutboxStatus.PENDING, EmailOutboxStatus.RETRY_WAIT]
                ),
                EmailOutbox.next_attempt_at <= now,
            )
            .order_by(col(EmailOutbox.next_attempt_at), col(EmailOutbox.id))
        ).all()
        if outbox_id is not None
    ]


def claim_delivery(
    *, session: Session, outbox_id: int, now: datetime
) -> DeliveryPayload | None:
    outbox = session.exec(
        select(EmailOutbox).where(EmailOutbox.id == outbox_id).with_for_update()
    ).one_or_none()
    if outbox is None or outbox.status in {
        EmailOutboxStatus.DELIVERED,
        EmailOutboxStatus.FAILED,
    }:
        return None
    if (
        outbox.status is EmailOutboxStatus.LEASED
        and outbox.lease_expires_at is not None
        and outbox.lease_expires_at > now
    ):
        return None
    if (
        outbox.status
        in {
            EmailOutboxStatus.PENDING,
            EmailOutboxStatus.RETRY_WAIT,
        }
        and outbox.next_attempt_at > now
    ):
        return None
    if outbox.status is EmailOutboxStatus.LEASED:
        _recover_expired_lease(session=session, outbox=outbox, now=now)
        return None
    if outbox.attempt_count >= MAX_ATTEMPTS:
        _mark_failed(
            session=session,
            outbox=outbox,
            category="MAX_ATTEMPTS_EXCEEDED",
            now=now,
        )
        return None
    rendered = _render_delivery(session=session, outbox=outbox)
    if rendered is None:
        _mark_failed(
            session=session,
            outbox=outbox,
            category="RECIPIENT_INVALID",
            now=now,
        )
        return None
    actor_id = (
        outbox.created_by
        if outbox.attempt_count == 0
        else require_system_actor(session=session)
    )
    bind_audit_actor(session=session, actor_id=actor_id)
    outbox.attempt_count += 1
    outbox.status = EmailOutboxStatus.LEASED
    outbox.lease_expires_at = now + LEASE_DURATION
    session.add(outbox)
    assert outbox.lease_expires_at is not None
    return DeliveryPayload(
        outbox_id=outbox_id,
        recipient=outbox.recipient,
        subject=rendered.subject,
        html_content=rendered.html_content,
        lease_expires_at=outbox.lease_expires_at,
    )


def complete_delivery(
    *, session: Session, payload: DeliveryPayload, now: datetime
) -> None:
    outbox = _locked_active_lease(session=session, payload=payload)
    if outbox is None:
        return
    bind_audit_actor(
        session=session, actor_id=_result_actor_id(session=session, outbox=outbox)
    )
    outbox.status = EmailOutboxStatus.DELIVERED
    outbox.delivered_at = now
    outbox.lease_expires_at = None
    outbox.last_error_category = None
    session.add(outbox)


def fail_delivery(
    *, session: Session, payload: DeliveryPayload, category: str, now: datetime
) -> None:
    outbox = _locked_active_lease(session=session, payload=payload)
    if outbox is None:
        return
    bind_audit_actor(
        session=session, actor_id=_result_actor_id(session=session, outbox=outbox)
    )
    outbox.lease_expires_at = None
    outbox.last_error_category = category
    if outbox.attempt_count >= MAX_ATTEMPTS:
        outbox.status = EmailOutboxStatus.FAILED
        outbox.failed_at = now
    else:
        outbox.status = EmailOutboxStatus.RETRY_WAIT
        outbox.next_attempt_at = now + RETRY_DELAY
    session.add(outbox)


def _locked_active_lease(
    *, session: Session, payload: DeliveryPayload
) -> EmailOutbox | None:
    outbox = session.exec(
        select(EmailOutbox).where(EmailOutbox.id == payload.outbox_id).with_for_update()
    ).one_or_none()
    if (
        outbox is None
        or outbox.status is not EmailOutboxStatus.LEASED
        or outbox.lease_expires_at != payload.lease_expires_at
    ):
        return None
    return outbox


def _recover_expired_lease(
    *, session: Session, outbox: EmailOutbox, now: datetime
) -> None:
    bind_audit_actor(session=session, actor_id=require_system_actor(session=session))
    outbox.lease_expires_at = None
    outbox.last_error_category = "DELIVERY_LEASE_EXPIRED"
    if outbox.attempt_count >= MAX_ATTEMPTS:
        outbox.status = EmailOutboxStatus.FAILED
        outbox.failed_at = now
    else:
        outbox.status = EmailOutboxStatus.RETRY_WAIT
        outbox.next_attempt_at = now
    session.add(outbox)


def _mark_failed(
    *, session: Session, outbox: EmailOutbox, category: str, now: datetime
) -> None:
    bind_audit_actor(session=session, actor_id=require_system_actor(session=session))
    outbox.status = EmailOutboxStatus.FAILED
    outbox.failed_at = now
    outbox.lease_expires_at = None
    outbox.last_error_category = category
    session.add(outbox)


def _result_actor_id(*, session: Session, outbox: EmailOutbox) -> uuid.UUID:
    if outbox.attempt_count == 1:
        return outbox.created_by
    return require_system_actor(session=session)


def _render_delivery(*, session: Session, outbox: EmailOutbox) -> _RenderedEmail | None:
    if outbox.kind is EmailOutboxKind.RENDERED:
        if outbox.subject is None or outbox.html_content is None:
            return None
        return _RenderedEmail(subject=outbox.subject, html_content=outbox.html_content)
    user = session.get(User, outbox.user_id)
    if (
        user is None
        or user.is_system_actor
        or not user.is_active
        or user.email != outbox.recipient
    ):
        return None
    if outbox.password_reset_version is None:
        return None
    purpose: Literal["password_reset", "password_setup"] = (
        "password_setup"
        if outbox.kind is EmailOutboxKind.ACCOUNT_SET_PASSWORD
        else "password_reset"
    )
    token = generate_password_reset_token(
        user_id=user.id,
        purpose=purpose,
        version=outbox.password_reset_version,
    )
    if outbox.kind is EmailOutboxKind.ACCOUNT_SET_PASSWORD:
        email_data = generate_set_password_email(
            email_to=user.email, email=user.email, token=token
        )
    else:
        email_data = generate_reset_password_email(
            email_to=user.email, email=user.email, token=token
        )
    return _RenderedEmail(
        subject=email_data.subject,
        html_content=email_data.html_content,
    )


@dataclass(frozen=True)
class _RenderedEmail:
    subject: str
    html_content: str
