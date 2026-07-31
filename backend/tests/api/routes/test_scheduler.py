from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.scheduler import SchedulerJob, SchedulerRun

INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)


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
) -> None:
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
        json={"planned_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "scheduled task does not support backfill"
    assert response.json()["request_id"]
    assert list(db.exec(select(SchedulerRun.id)).all()) == before
