from typing import Any

from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings

celery_app: Any = Celery(
    "app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend_url,
    include=["app.core.tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": settings.CELERY_VISIBILITY_TIMEOUT_SECONDS
    },
    result_expires=settings.CELERY_RESULT_EXPIRES_SECONDS,
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    worker_prefetch_multiplier=1,
)
