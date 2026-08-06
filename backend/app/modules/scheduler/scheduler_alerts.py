import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.audit import bind_audit_actor, clear_audit_actor
from app.core.config import settings
from app.core.db import engine
from app.core.observability import log_event
from app.models.scheduler import SchedulerJob
from app.modules.scheduler.config import scheduler_settings
from app.modules.scheduler.run_lifecycle import utc_now
from app.services.email_outbox import queue_rendered_email

ALERT_INTERVAL = timedelta(hours=1)


def clear_success_alerts(*, session: Session, job_id: int) -> None:
    job = session.get(SchedulerJob, job_id)
    if job is None:
        return
    job.run_failure_alerted_at = None
    job.overlap_alerted_at = None
    session.add(job)


def send_alert(
    *,
    job_id: int,
    kind: str,
    category: str,
    summary: str,
    planned_at: datetime,
    actor_id: uuid.UUID,
) -> None:
    now = utc_now()
    recipients = scheduler_settings.SCHEDULED_TASK_ALERT_RECIPIENTS
    emit_unsent = False
    with Session(engine) as session:
        bind_audit_actor(session=session, actor_id=actor_id)
        try:
            job = session.exec(
                select(SchedulerJob).where(SchedulerJob.id == job_id).with_for_update()
            ).one_or_none()
            if job is None:
                return
            if kind == "OVERLAP":
                alerted_at = job.overlap_alerted_at
            elif kind == "CONFIGURATION":
                alerted_at = job.configuration_alerted_at
            else:
                alerted_at = job.run_failure_alerted_at
            if alerted_at is not None and now - alerted_at < ALERT_INTERVAL:
                return
            if kind == "OVERLAP":
                job.overlap_alerted_at = now
            elif kind == "CONFIGURATION":
                job.configuration_alerted_at = now
            else:
                job.run_failure_alerted_at = now
            session.add(job)
            if recipients:
                subject = f"{settings.PROJECT_NAME} - Scheduled task alert"
                content = (
                    f"<p>Task: {job.name} (#{job_id})</p>"
                    f"<p>Category: {category}</p>"
                    f"<p>Planned at: {planned_at}</p>"
                    f"<p>Summary: {summary}</p>"
                )
                for recipient in recipients:
                    queue_rendered_email(
                        session=session,
                        recipient=str(recipient),
                        subject=subject,
                        html_content=content,
                    )
            else:
                emit_unsent = True
            session.commit()
        finally:
            clear_audit_actor(session=session)
    if emit_unsent:
        log_event(event_name="scheduler.alert.unsent", severity="WARNING")
