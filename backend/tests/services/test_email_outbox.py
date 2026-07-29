from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from app.core.audit import bind_audit_actor
from app.core.config import settings
from app.core.tasks import deliver_outbox_email
from app.models import EmailOutbox, EmailOutboxStatus, User
from app.services import email_outbox
from tests.utils.user import create_random_user


@pytest.fixture(autouse=True)
def bind_first_superuser(db: Session) -> None:
    actor = db.exec(select(User).where(User.email == settings.FIRST_SUPERUSER)).one()
    bind_audit_actor(session=db, actor_id=actor.id)


def _queue_rendered(db: Session) -> EmailOutbox:
    outbox = email_outbox.queue_rendered_email(
        session=db,
        recipient="recipient@example.com",
        subject="Subject",
        html_content="<p>Body</p>",
    )
    db.commit()
    assert outbox.id is not None
    return outbox


def test_delivery_succeeds_once(db: Session) -> None:
    outbox = _queue_rendered(db)

    with patch("app.core.tasks.send_email") as send_email:
        deliver_outbox_email(outbox.id or 0)
        deliver_outbox_email(outbox.id or 0)

    db.expire_all()
    persisted = db.get(EmailOutbox, outbox.id)
    assert persisted is not None
    assert persisted.status is EmailOutboxStatus.DELIVERED
    assert persisted.attempt_count == 1
    assert persisted.delivered_at is not None
    send_email.assert_called_once()


def test_missing_smtp_retries(db: Session, monkeypatch) -> None:
    outbox = _queue_rendered(db)
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    deliver_outbox_email(outbox.id or 0)

    db.expire_all()
    persisted = db.get(EmailOutbox, outbox.id)
    assert persisted is not None
    assert persisted.status is EmailOutboxStatus.RETRY_WAIT
    assert persisted.attempt_count == 1
    assert persisted.last_error_category == "SMTP_NOT_CONFIGURED"
    assert persisted.next_attempt_at > datetime.now(UTC)


def test_link_delivery_marks_invalid_recipient_terminal(db: Session) -> None:
    user = create_random_user(db)
    outbox = email_outbox.queue_password_recovery_email(session=db, user=user)
    user.is_active = False
    db.add(user)
    db.commit()
    assert outbox.id is not None

    deliver_outbox_email(outbox.id)

    db.expire_all()
    persisted = db.get(EmailOutbox, outbox.id)
    assert persisted is not None
    assert persisted.status is EmailOutboxStatus.FAILED
    assert persisted.last_error_category == "RECIPIENT_INVALID"
    assert persisted.attempt_count == 0


def test_expired_eighth_lease_becomes_terminal(db: Session) -> None:
    outbox = _queue_rendered(db)
    now = datetime(2026, 7, 29, tzinfo=UTC)
    outbox.status = EmailOutboxStatus.LEASED
    outbox.attempt_count = 8
    outbox.lease_expires_at = now - timedelta(seconds=1)
    db.add(outbox)
    db.commit()

    email_outbox.recover_expired_leases(session=db, now=now)
    db.commit()

    db.expire_all()
    persisted = db.get(EmailOutbox, outbox.id)
    assert persisted is not None
    assert persisted.status is EmailOutboxStatus.FAILED
    assert persisted.failed_at == now
    assert persisted.last_error_category == "DELIVERY_LEASE_EXPIRED"


def test_claiming_expired_lease_only_recovers_it(db: Session) -> None:
    outbox = _queue_rendered(db)
    now = datetime(2026, 7, 29, tzinfo=UTC)
    outbox.status = EmailOutboxStatus.LEASED
    outbox.attempt_count = 1
    outbox.lease_expires_at = now - timedelta(seconds=1)
    db.add(outbox)
    db.commit()

    payload = email_outbox.claim_delivery(session=db, outbox_id=outbox.id or 0, now=now)
    db.commit()

    db.expire_all()
    persisted = db.get(EmailOutbox, outbox.id)
    assert payload is None
    assert persisted is not None
    assert persisted.status is EmailOutboxStatus.RETRY_WAIT
    assert persisted.last_error_category == "DELIVERY_LEASE_EXPIRED"
