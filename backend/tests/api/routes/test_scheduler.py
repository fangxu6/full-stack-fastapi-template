from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.scheduler import SchedulerJob, SchedulerRun
from app.modules.scheduler.contracts import ScheduledTask, ScheduledTaskConfig

INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)
REPLAY_SAFE_BACKFILL_CLASS = (
    "app.modules.scheduler.scheduled_tasks.ReplaySafeBackfillTask"
)


class ReplaySafeBackfillTask(ScheduledTask):
    config_model = ScheduledTaskConfig
    allow_backfill = True

    def run(self, *, context: object, config: ScheduledTaskConfig) -> None:
        del context, config


def test_scheduler_previews_cron_without_side_effects(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 26, 0, 0, tzinfo=UTC)
    monkeypatch.setattr("app.modules.scheduler.service.get_datetime_utc", lambda: now)
    before_job_ids = list(db.exec(select(SchedulerJob.id)).all())
    before_run_ids = list(db.exec(select(SchedulerRun.id)).all())

    response = client.get(
        "/api/v1/scheduler/cron-preview",
        headers=superuser_token_headers,
        params={"cron_expression": "0 8 * * *"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "base_at": "2026-07-26T00:00:00Z",
        "timezone": "Asia/Shanghai",
        "next_run_ats": [
            "2026-07-27T00:00:00Z",
            "2026-07-28T00:00:00Z",
            "2026-07-29T00:00:00Z",
            "2026-07-30T00:00:00Z",
            "2026-07-31T00:00:00Z",
        ],
    }
    assert list(db.exec(select(SchedulerJob.id)).all()) == before_job_ids
    assert list(db.exec(select(SchedulerRun.id)).all()) == before_run_ids


def test_scheduler_preview_rejects_invalid_cron_without_side_effects(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    before_job_ids = list(db.exec(select(SchedulerJob.id)).all())
    before_run_ids = list(db.exec(select(SchedulerRun.id)).all())

    response = client.get(
        "/api/v1/scheduler/cron-preview",
        headers=superuser_token_headers,
        params={"cron_expression": "0 8 * *"},
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"] == "cron expression must contain exactly five fields"
    )
    assert response.json()["request_id"]
    assert list(db.exec(select(SchedulerJob.id)).all()) == before_job_ids
    assert list(db.exec(select(SchedulerRun.id)).all()) == before_run_ids


def test_scheduler_preview_requires_read_permission(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/scheduler/cron-preview",
        headers=normal_user_token_headers,
        params={"cron_expression": "0 8 * * *"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user does not have the required permission"
    assert response.json()["request_id"]


def test_scheduler_rejects_credential_config_before_creating_a_job(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    before = list(db.exec(select(SchedulerJob.id)).all())

    response = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Credential config",
            "class_path": INVENTORY_RETRY_CLASS,
            "cron_expression": "0 8 * * *",
            "config": {"authorization": "Bearer value"},
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "scheduled task configuration cannot contain credentials"
    )
    assert list(db.exec(select(SchedulerJob.id)).all()) == before


def test_scheduler_job_management_flow(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dispatch_calls: list[dict[str, object]] = []

    def record_dispatch(**kwargs: object) -> None:
        dispatch_calls.append(kwargs)

    monkeypatch.setattr(
        "app.modules.scheduler.tasks.dispatch_queued_runs", record_dispatch
    )
    invalid = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Invalid",
            "class_path": "os.system",
            "cron_expression": "0 8 * * *",
            "config": {},
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Manual retry",
            "class_path": INVENTORY_RETRY_CLASS,
            "cron_expression": "*/15 * * * *",
            "config": {},
        },
    )
    assert created.status_code == 200
    job = created.json()
    assert not job["enabled"]
    assert job["can_run_now"]
    assert not job["can_backfill"]

    schema = client.get(
        "/api/v1/scheduler/task-schema",
        headers=superuser_token_headers,
        params={"class_path": INVENTORY_RETRY_CLASS},
    )
    assert schema.status_code == 200
    assert schema.json()["json_schema"]["type"] == "object"

    enabled = client.post(
        f"/api/v1/scheduler/jobs/{job['id']}/enable",
        headers=superuser_token_headers,
    )
    assert enabled.status_code == 200
    assert enabled.json()["enabled"]

    queued = client.post(
        f"/api/v1/scheduler/jobs/{job['id']}/run-now",
        headers=superuser_token_headers,
    )
    assert queued.status_code == 200
    assert queued.json()["trigger"] == "MANUAL_NOW"
    assert dispatch_calls == []
    assert (
        client.post(
            f"/api/v1/scheduler/jobs/{job['id']}/run-now",
            headers=superuser_token_headers,
        ).status_code
        == 409
    )

    runs = client.get(
        f"/api/v1/scheduler/jobs/{job['id']}/runs",
        headers=superuser_token_headers,
    )
    assert runs.status_code == 200
    assert runs.json()["count"] == 1

    disabled = client.post(
        f"/api/v1/scheduler/jobs/{job['id']}/disable",
        headers=superuser_token_headers,
    )
    assert disabled.status_code == 200
    deleted = client.delete(
        f"/api/v1/scheduler/jobs/{job['id']}", headers=superuser_token_headers
    )
    assert deleted.status_code == 200
    assert (
        client.get(
            f"/api/v1/scheduler/jobs/{job['id']}", headers=superuser_token_headers
        ).status_code
        == 404
    )
    restored = client.post(
        f"/api/v1/scheduler/jobs/{job['id']}/restore",
        headers=superuser_token_headers,
    )
    assert restored.status_code == 200
    assert not restored.json()["enabled"]


def test_scheduler_rejects_unsupported_backfill_without_creating_a_run(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    monkeypatch.setattr("app.modules.scheduler.service.get_datetime_utc", lambda: now)
    created = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Daily report retry",
            "class_path": INVENTORY_RETRY_CLASS,
            "cron_expression": "* * * * *",
            "config": {},
        },
    )
    assert created.status_code == 200
    job_id = created.json()["id"]
    before = list(db.exec(select(SchedulerRun.id)).all())

    response = client.post(
        f"/api/v1/scheduler/jobs/{job_id}/backfill",
        headers=superuser_token_headers,
        json={"planned_at": (now - timedelta(days=365)).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "scheduled task does not support backfill"
    assert response.json()["request_id"]
    assert list(db.exec(select(SchedulerRun.id)).all()) == before


def test_scheduler_backfill_creates_one_run_at_the_365_day_boundary(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 7, 31, 0, 0, tzinfo=UTC)
    planned_at = now - timedelta(days=365)
    monkeypatch.setattr("app.modules.scheduler.service.get_datetime_utc", lambda: now)
    monkeypatch.setattr(
        "app.modules.scheduler.service.resolve_task_class",
        lambda _: ReplaySafeBackfillTask,
    )
    created = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Replay-safe backfill",
            "class_path": REPLAY_SAFE_BACKFILL_CLASS,
            "cron_expression": "0 8 * * *",
            "config": {},
        },
    )
    assert created.status_code == 200
    job_id = created.json()["id"]
    before = list(db.exec(select(SchedulerRun.id)).all())

    response = client.post(
        f"/api/v1/scheduler/jobs/{job_id}/backfill",
        headers=superuser_token_headers,
        json={"planned_at": planned_at.isoformat()},
    )

    assert response.status_code == 200
    assert response.json()["trigger"] == "MANUAL_BACKFILL"
    assert response.json()["status"] == "QUEUED"
    assert response.json()["planned_at"] == "2025-07-31T00:00:00Z"
    assert response.json()["class_path"] == REPLAY_SAFE_BACKFILL_CLASS
    run_ids = list(db.exec(select(SchedulerRun.id)).all())
    assert len(run_ids) == len(before) + 1
    run = db.get(SchedulerRun, response.json()["id"])
    assert run is not None
    assert run.next_dispatch_at == now

    conflict = client.post(
        f"/api/v1/scheduler/jobs/{job_id}/backfill",
        headers=superuser_token_headers,
        json={"planned_at": planned_at.isoformat()},
    )

    assert conflict.status_code == 409
    assert list(db.exec(select(SchedulerRun.id)).all()) == run_ids


def test_scheduler_backfill_requires_manage_permission(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Backfill permission",
            "class_path": INVENTORY_RETRY_CLASS,
            "cron_expression": "* * * * *",
            "config": {},
        },
    )
    assert created.status_code == 200
    before = list(db.exec(select(SchedulerRun.id)).all())

    response = client.post(
        f"/api/v1/scheduler/jobs/{created.json()['id']}/backfill",
        headers=normal_user_token_headers,
        json={"planned_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user does not have the required permission"
    assert response.json()["request_id"]
    assert list(db.exec(select(SchedulerRun.id)).all()) == before


def test_scheduler_keeps_invalid_task_definitions_manageable(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/v1/scheduler/jobs",
        headers=superuser_token_headers,
        json={
            "name": "Retired task definition",
            "class_path": INVENTORY_RETRY_CLASS,
            "cron_expression": "* * * * *",
            "config": {},
        },
    )
    assert created.status_code == 200
    job_id = created.json()["id"]
    job = db.get(SchedulerJob, job_id)
    assert job is not None
    job.class_path = "app.modules.inventory.scheduled_tasks.RetiredTask"
    db.add(job)
    db.commit()
    before = list(db.exec(select(SchedulerRun.id)).all())

    listed = client.get("/api/v1/scheduler/jobs", headers=superuser_token_headers)
    assert listed.status_code == 200
    listed_job = next(item for item in listed.json()["data"] if item["id"] == job_id)
    assert not listed_job["can_run_now"]
    assert not listed_job["can_backfill"]

    detail = client.get(
        f"/api/v1/scheduler/jobs/{job_id}", headers=superuser_token_headers
    )
    assert detail.status_code == 200
    assert not detail.json()["can_run_now"]
    assert not detail.json()["can_backfill"]

    run_now = client.post(
        f"/api/v1/scheduler/jobs/{job_id}/run-now",
        headers=superuser_token_headers,
    )
    assert run_now.status_code == 422
    assert run_now.json()["detail"] == "scheduled task class must inherit ScheduledTask"
    assert run_now.json()["request_id"]

    backfill = client.post(
        f"/api/v1/scheduler/jobs/{job_id}/backfill",
        headers=superuser_token_headers,
        json={"planned_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )
    assert backfill.status_code == 422
    assert (
        backfill.json()["detail"] == "scheduled task class must inherit ScheduledTask"
    )
    assert backfill.json()["request_id"]
    assert list(db.exec(select(SchedulerRun.id)).all()) == before
