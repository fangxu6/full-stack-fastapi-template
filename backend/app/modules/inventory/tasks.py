from sqlmodel import Session

from app.core.celery import celery_app
from app.core.db import engine
from app.modules.inventory.daily_report import (
    create_daily_reports,
    deliver_daily_report_email,
    queue_due_daily_report_deliveries,
)


def _enqueue(delivery_ids: list[int]) -> None:
    for delivery_id in delivery_ids:
        celery_app.tasks["inventory.daily_report.deliver"].delay(delivery_id)


def create_inventory_daily_reports() -> None:
    with Session(engine) as session:
        create_daily_reports(session=session)
        delivery_ids = queue_due_daily_report_deliveries(session=session)
    _enqueue(delivery_ids)


def retry_inventory_daily_report_deliveries() -> None:
    with Session(engine) as session:
        delivery_ids = queue_due_daily_report_deliveries(session=session)
    _enqueue(delivery_ids)


celery_app.task(name="inventory.daily_report.create", ignore_result=True)(
    create_inventory_daily_reports
)
celery_app.task(name="inventory.daily_report.retry", ignore_result=True)(
    retry_inventory_daily_report_deliveries
)
celery_app.task(name="inventory.daily_report.deliver", ignore_result=True)(
    deliver_daily_report_email
)
