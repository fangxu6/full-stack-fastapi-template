from sqlmodel import Session

from app.core.celery import celery_app
from app.core.db import engine
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


class InventoryDailyReportCreateTask(ScheduledTask):
    config_model = ScheduledTaskConfig

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

    def run(
        self, *, context: ScheduledTaskContext, config: ScheduledTaskConfig
    ) -> None:
        del context, config
        with Session(engine) as session:
            delivery_ids = queue_due_daily_report_deliveries(session=session)
        for delivery_id in delivery_ids:
            celery_app.tasks["inventory.daily_report.deliver"].delay(delivery_id)
