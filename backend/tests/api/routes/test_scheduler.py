import pytest
from fastapi.testclient import TestClient

INVENTORY_RETRY_CLASS = (
    "app.modules.inventory.scheduled_tasks.InventoryDailyReportRetryTask"
)


def test_scheduler_job_management_flow(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.core.celery.celery_app.send_task", lambda *_, **__: None
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
