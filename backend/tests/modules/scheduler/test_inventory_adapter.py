import uuid
from datetime import UTC, datetime

import pytest

from app.models.scheduler import SchedulerRunTrigger
from app.modules.inventory.scheduled_tasks import InventoryDailyReportCreateTask
from app.modules.scheduler.contracts import (
    ScheduledTaskConfig,
    ScheduledTaskContext,
    ScheduledTaskSkipped,
)


def test_inventory_daily_report_adapter_skips_after_grace_window() -> None:
    context = ScheduledTaskContext(
        run_id=1,
        actor_id=uuid.uuid4(),
        trigger=SchedulerRunTrigger.SCHEDULED,
        planned_at=datetime(2026, 7, 26, 0, 0, tzinfo=UTC),
        started_at=datetime(2026, 7, 26, 0, 16, tzinfo=UTC),
    )

    with pytest.raises(ScheduledTaskSkipped, match="window expired"):
        InventoryDailyReportCreateTask().run(
            context=context, config=ScheduledTaskConfig()
        )
