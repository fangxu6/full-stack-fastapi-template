from app.core.celery import celery_app
from app.modules.scheduler import orchestration

# Keep the dispatch helper importable for existing management tests and callers;
# Celery entrypoints themselves remain adapters over orchestration.
dispatch_queued_runs = orchestration.dispatch_queued_runs

celery_app.task(name="scheduler.scan_due_jobs", ignore_result=True)(
    orchestration.scan_due_jobs
)
celery_app.task(name="scheduler.execute_run", ignore_result=True)(
    orchestration.execute_run
)
celery_app.task(name="scheduler.cleanup_runs", ignore_result=True)(
    orchestration.cleanup_scheduled_runs
)
