from sqlmodel import Session

from app.core.audit import bind_audit_actor, clear_audit_actor, require_system_actor
from app.core.celery import celery_app
from app.core.config import settings
from app.core.db import engine
from app.services import email_outbox
from app.utils import generate_test_email, send_email


def runtime_ping(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("runtime.ping value must be a string")
    if len(value) > 64:
        raise ValueError("runtime.ping value must be 64 characters or fewer")
    return value


def send_scheduled_test_email() -> None:
    email_to = str(settings.EMAIL_TEST_USER)
    email_data = generate_test_email(email_to=email_to)
    with Session(engine) as session:
        bind_audit_actor(
            session=session, actor_id=require_system_actor(session=session)
        )
        try:
            email_outbox.queue_rendered_email(
                session=session,
                recipient=email_to,
                subject=email_data.subject,
                html_content=email_data.html_content,
            )
            session.commit()
        finally:
            clear_audit_actor(session=session)


def scan_due_email_outbox() -> None:
    now = email_outbox.utc_now()
    with Session(engine) as session:
        bind_audit_actor(
            session=session, actor_id=require_system_actor(session=session)
        )
        try:
            email_outbox.recover_expired_leases(session=session, now=now)
            outbox_ids = email_outbox.due_outbox_ids(session=session, now=now)
            session.commit()
        finally:
            clear_audit_actor(session=session)
    for outbox_id in outbox_ids:
        try:
            celery_app.tasks["email_outbox.deliver"].delay(outbox_id)
        except Exception:
            pass


def deliver_outbox_email(outbox_id: int) -> None:
    if not isinstance(outbox_id, int):
        raise ValueError("email outbox id must be an integer")
    with Session(engine) as session:
        try:
            payload = email_outbox.claim_delivery(
                session=session, outbox_id=outbox_id, now=email_outbox.utc_now()
            )
            session.commit()
        finally:
            clear_audit_actor(session=session)
    if payload is None:
        return
    error_category: str | None = None
    try:
        if not settings.emails_enabled:
            error_category = "SMTP_NOT_CONFIGURED"
        else:
            send_email(
                email_to=payload.recipient,
                subject=payload.subject,
                html_content=payload.html_content,
            )
    except Exception:
        error_category = "SMTP_DELIVERY_FAILED"
    with Session(engine) as session:
        try:
            if error_category is None:
                email_outbox.complete_delivery(
                    session=session, payload=payload, now=email_outbox.utc_now()
                )
            else:
                email_outbox.fail_delivery(
                    session=session,
                    payload=payload,
                    category=error_category,
                    now=email_outbox.utc_now(),
                )
            session.commit()
        finally:
            clear_audit_actor(session=session)


celery_app.task(name="runtime.ping")(runtime_ping)
celery_app.task(name="runtime.send_test_email", ignore_result=True)(
    send_scheduled_test_email
)
celery_app.task(name="email_outbox.scan_due", ignore_result=True)(scan_due_email_outbox)
celery_app.task(name="email_outbox.deliver", ignore_result=True)(deliver_outbox_email)
