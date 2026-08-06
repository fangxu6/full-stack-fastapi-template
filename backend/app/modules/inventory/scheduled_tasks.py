from sqlmodel import Session

from app.core.audit import bind_audit_actor, clear_audit_actor
from app.core.celery import celery_app
from app.core.db import engine
from app.models.base import get_datetime_utc
from app.models.inventory import InventoryCorrectionFailureCategory
from app.modules.inventory import correction_attempts
from app.modules.inventory.daily_report import (
    create_daily_reports,
    queue_due_daily_report_deliveries,
    report_date_for_scheduled_run,
)
from app.modules.scheduler.contracts import (
    ScheduledTask,
    ScheduledTaskConfig,
    ScheduledTaskContext,
    ScheduledTaskSkipped,
)
from app.modules.scheduler.service import LEASE_DURATION


class InventoryDailyReportCreateTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_backfill = False

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del config
        if report_date_for_scheduled_run(context.started_at) is None:
            raise ScheduledTaskSkipped(
                "DAILY_REPORT_WINDOW_EXPIRED",
                "Inventory daily report window expired",
            )
        with Session(engine) as session:
            create_daily_reports(session=session, now=context.started_at)
            delivery_ids = queue_due_daily_report_deliveries(
                session=session, now=context.started_at
            )
        for delivery_id in delivery_ids:
            celery_app.tasks["inventory.daily_report.deliver"].delay(delivery_id)


class InventoryDailyReportRetryTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_backfill = False

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config
        with Session(engine) as session:
            delivery_ids = queue_due_daily_report_deliveries(session=session)
        for delivery_id in delivery_ids:
            celery_app.tasks["inventory.daily_report.deliver"].delay(delivery_id)


class InventoryCorrectionApplyTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_run_now = False
    allow_backfill = False

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del config
        now = get_datetime_utc()
        with Session(engine) as session:
            bind_audit_actor(session=session, actor_id=context.actor_id)
            try:
                correction_attempts.mark_expired_attempts_terminal(
                    session=session, now=now
                )
                claimed_attempts = correction_attempts.claim_pending_attempts(
                    session=session,
                    scheduler_run_id=context.run_id,
                    now=now,
                    lease_duration=LEASE_DURATION,
                )
                session.commit()
            finally:
                clear_audit_actor(session=session)
        for work_item_id, attempt_id in claimed_attempts:
            self._apply_claimed_attempt(
                context=context,
                work_item_id=work_item_id,
                attempt_id=attempt_id,
            )

    @staticmethod
    def _apply_claimed_attempt(
        *, context: ScheduledTaskContext, work_item_id: int, attempt_id: int
    ) -> None:
        with Session(engine) as session:
            bind_audit_actor(session=session, actor_id=context.actor_id)
            try:
                try:
                    correction_attempts.apply_claimed_attempt(
                        session=session,
                        work_item_id=work_item_id,
                        attempt_id=attempt_id,
                        scheduler_run_id=context.run_id,
                        actor_user_id=context.actor_id,
                        now=get_datetime_utc(),
                    )
                    session.commit()
                except correction_attempts.CorrectionApplicationError as error:
                    session.rollback()
                    correction_attempts.finalize_failed_attempt(
                        session=session,
                        work_item_id=work_item_id,
                        attempt_id=attempt_id,
                        category=error.category,
                        now=get_datetime_utc(),
                    )
                    session.commit()
                except Exception:
                    session.rollback()
                    correction_attempts.finalize_failed_attempt(
                        session=session,
                        work_item_id=work_item_id,
                        attempt_id=attempt_id,
                        category=InventoryCorrectionFailureCategory.EXECUTION_FAILED,
                        now=get_datetime_utc(),
                    )
                    session.commit()
            finally:
                clear_audit_actor(session=session)
