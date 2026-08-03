from sqlmodel import Session

from app.core.celery import celery_app
from app.core.db import engine
from app.modules.audit.service import cleanup_expired_events


def cleanup_audit_events() -> None:
    with Session(engine) as session:
        cleanup_expired_events(session=session)
        session.commit()


celery_app.task(name="audit.cleanup_events", ignore_result=True)(cleanup_audit_events)
