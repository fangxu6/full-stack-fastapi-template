from app.core.celery import celery_app
from app.modules.inventory.daily_report import deliver_daily_report_email

celery_app.task(name="inventory.daily_report.deliver", ignore_result=True)(
    deliver_daily_report_email
)
